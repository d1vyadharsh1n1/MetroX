import { Layout, Menu } from 'antd'
import { HomeOutlined, DashboardOutlined, AppstoreOutlined, PlayCircleOutlined, ToolOutlined, DatabaseOutlined } from '@ant-design/icons'
import { Link, Route, Routes, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import './App.css'
import metroxLogo from './assets/metrox.jpg'
import Home from './pages/Home.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Scheduler from './pages/Scheduler.jsx'
import ManualModifications from './pages/ManualModifications.jsx'
import DataViewer from './pages/DataViewer.jsx'

const { Header, Content } = Layout

function App() {
  const location = useLocation()
  const selectedKey = location.pathname === '/' ? '/' : location.pathname

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header className="app-shell-header">
        <div className="navbar-container">
          <div className="navbar-brand">
            <div className="brand-logo">
              <img 
                src={metroxLogo} 
                alt="MetroX Logo" 
                style={{ 
                  width: 32, 
                  height: 32, 
                  objectFit: 'contain',
                  borderRadius: '50%'
                }} 
              />
            </div>
            <div className="brand-text">
              <div className="brand-title">MetroX</div>
              <div className="brand-subtitle">Scheduler</div>
            </div>
          </div>
          
          <Menu 
            mode="horizontal" 
            selectedKeys={[selectedKey]} 
            className="navbar-menu"
            items={[
              { key: '/', icon: <HomeOutlined />, label: <Link to="/">Home</Link> },
              { key: '/dashboard', icon: <DashboardOutlined />, label: <Link to="/dashboard">Dashboard</Link> },
              { key: '/scheduler', icon: <AppstoreOutlined />, label: <Link to="/scheduler">Scheduler</Link> },
              { key: '/modifications', icon: <ToolOutlined />, label: <Link to="/modifications">Manual Modifications</Link> },
              { key: '/data', icon: <DatabaseOutlined />, label: <Link to="/data">Data Viewer</Link> },
            ]}
          />
        </div>
      </Header>
      <Content style={{ margin: 16 }}>
        <div className="page-container" style={{ minHeight: 'calc(100vh - 120px)' }}>
          <AnimatePresence mode="wait">
            <motion.div key={location.pathname} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.18 }}>
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/scheduler" element={<Scheduler />} />
                <Route path="/modifications" element={<ManualModifications />} />
                <Route path="/data" element={<DataViewer />} />
              </Routes>
            </motion.div>
          </AnimatePresence>
        </div>
      </Content>
    </Layout>
  )
}

export default App
