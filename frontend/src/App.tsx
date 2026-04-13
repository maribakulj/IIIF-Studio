import { Routes, Route } from 'react-router-dom'
import Admin from './pages/Admin.tsx'
import Editor from './pages/Editor.tsx'
import Home from './pages/Home.tsx'
import Reader from './pages/Reader.tsx'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/admin" element={<Admin />} />
      <Route path="/reader/:manuscriptId" element={<Reader />} />
      <Route path="/editor/:pageId" element={<Editor />} />
    </Routes>
  )
}
