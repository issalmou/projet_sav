import { Outlet } from 'react-router-dom'
import LeftSidebar from './LeftSidebar'
import TopNavBar from './TopNavBar'

function Layout() {
  return (
    <div className="flex min-h-screen">
      <LeftSidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopNavBar />
        <Outlet />
      </div>
    </div>
  )
}

export default Layout