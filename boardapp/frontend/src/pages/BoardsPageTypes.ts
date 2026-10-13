export interface BoardsList {
  own: { id: string; title: string }[]
  shared: { id: string; title: string; role: string }[]
}
