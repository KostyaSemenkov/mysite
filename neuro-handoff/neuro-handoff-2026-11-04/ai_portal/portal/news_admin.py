from django.contrib import admin, messages
from django import forms
from django.core.exceptions import ValidationError, PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseNotAllowed
from django.urls import path, reverse
from django.utils.html import format_html
from .news_models import NewsSource, IncomingNews, ImportRun
from .news.service import mark_ready, publish, reject, revision, check_revision

class IncomingNewsForm(forms.ModelForm):
    revision = forms.CharField(widget=forms.HiddenInput)
    class Meta:
        model=IncomingNews
        fields=['title_ru','summary_ru','body_ru','event','editor_note']
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if self.instance.pk: self.initial['revision']=revision(self.instance)
    def clean(self):
        data=super().clean()
        if self.instance.pk:
            current=IncomingNews.objects.select_for_update().get(pk=self.instance.pk)
            check_revision(current,data.get('revision',''))
        return data

@admin.register(NewsSource)
class NewsSourceAdmin(admin.ModelAdmin):
    list_display=['company','enabled','last_success','last_checked','last_error']
    readonly_fields=['company','initialized','last_checked','last_success','last_error']
    fields=['company','enabled','initialized','last_checked','last_success','last_error']
    def has_add_permission(self,request): return False
    def has_delete_permission(self,request,obj=None): return False

@admin.register(IncomingNews)
class IncomingNewsAdmin(admin.ModelAdmin):
    form=IncomingNewsForm
    list_display=['__str__','source','event','status','source_date','preview_link']
    list_filter=['status','source','event']
    search_fields=['title_ru','original_title','summary_ru']
    readonly_fields=['source','source_url','original_title','original_text','previous_text','source_date','status','fetched_at','updated_at','publication','approved_by','approved_at','preview_link']
    fields=['revision','source','status','preview_link','title_ru','summary_ru','body_ru','event','editor_note','source_url','source_date','original_title','original_text','previous_text','publication','fetched_at','updated_at','approved_by','approved_at']
    actions=['ready','approve','reject']
    def has_add_permission(self,request): return False
    def has_delete_permission(self,request,obj=None): return False
    def get_urls(self):
        return [path('<int:pk>/preview/',self.admin_site.admin_view(self.preview),name='china_preview')]+super().get_urls()
    @admin.display(description='Предпросмотр')
    def preview_link(self,obj):
        return format_html('<a href="{}">Открыть черновик</a>',reverse('admin:china_preview',args=[obj.pk]))
    def preview(self,request,pk):
        if request.method not in ['GET','POST']: return HttpResponseNotAllowed(['GET','POST'])
        item=get_object_or_404(IncomingNews,pk=pk)
        if not self.has_view_permission(request,item): raise PermissionDenied
        can_change=self.has_change_permission(request,item)
        can_publish=can_change and request.user.has_perms(['portal.add_publication','portal.change_publication'])
        if request.method=='POST':
            if not can_change: raise PermissionDenied
            action=request.POST.get('action')
            try:
                expected=request.POST.get('revision','')
                if action=='publish':
                    if not can_publish: raise PermissionDenied
                    publish(item,request.user,expected)
                    message='Новость опубликована. Она доступна в разделе «Китайские нейросети».'
                elif action=='ready':
                    mark_ready(item,expected)
                    message='Русский текст готов к проверке. Публикация требует отдельного одобрения.'
                elif action=='reject':
                    reject(item,expected)
                    message='Черновик отклонён. Уже опубликованная версия, если она есть, остаётся на сайте.'
                else:
                    raise ValidationError('Неизвестное действие.')
                self.log_change(request,item,message)
                self.message_user(request,message,messages.SUCCESS)
            except ValidationError as exc:
                self.message_user(request,exc.messages[0],messages.ERROR)
            return redirect('admin:china_preview',pk=item.pk)
        return render(request,'china_preview.html',{'item':item,'revision':revision(item),'can_change':can_change,'can_publish':can_publish})
    def save_model(self,request,obj,form,change):
        # Editing a previously reviewed summary invalidates its approval stage.
        if any(f in form.changed_data for f in ['title_ru','summary_ru','body_ru']):
            obj.status='waiting';obj.summary_source_hash=''
        fields=set(form.changed_data)&{'title_ru','summary_ru','body_ru','event','editor_note'}
        if fields&{'title_ru','summary_ru','body_ru'}: fields.update(['status','summary_source_hash'])
        obj.save(update_fields=fields|{'updated_at'})
    @admin.action(description='1. Русский текст подготовлен — отправить на проверку',permissions=['change'])
    def ready(self,request,queryset):
        count=0
        for item in queryset:
            try: mark_ready(item);count+=1
            except ValidationError as exc:self.message_user(request,f'{item}: {exc.messages[0]}',messages.ERROR)
        self.message_user(request,f'Готово к проверке: {count}.',messages.SUCCESS)
    @admin.action(description='2. Одобрить и опубликовать выбранные новости',permissions=['change'])
    def approve(self,request,queryset):
        if not request.user.has_perms(['portal.add_publication','portal.change_publication']): raise PermissionDenied
        count=0
        for item in queryset:
            try:publish(item,request.user);count+=1
            except ValidationError as exc:self.message_user(request,f'{item}: {exc.messages[0]}',messages.ERROR)
        self.message_user(request,f'Опубликовано: {count}.',messages.SUCCESS)
    @admin.action(description='Отклонить (не удаляет уже опубликованную версию)',permissions=['change'])
    def reject(self,request,queryset):
        for item in queryset: reject(item)

@admin.register(ImportRun)
class ImportRunAdmin(admin.ModelAdmin):
    list_display=['source','started_at','finished_at','created','changed','skipped','error']
    list_filter=['source']
    readonly_fields=['source','started_at','finished_at','created','changed','skipped','error']
    def has_add_permission(self,request):return False
    def has_change_permission(self,request,obj=None):return False
    def has_delete_permission(self,request,obj=None):return False
