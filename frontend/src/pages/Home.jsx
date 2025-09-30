import { Button, Card, Col, Row, Typography, Statistic, Empty } from 'antd'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useState, useEffect } from 'react'
import axios from 'axios'
import MetroXLogo from '../components/MetroXLogo'
import trainImg from '../assets/train.jpg'
import metroxLogo from '../assets/metrox.jpg'

const { Title, Paragraph, Text } = Typography

export default function Home() {
  const [schedule, setSchedule] = useState([])
  const [hoveredTrain, setHoveredTrain] = useState(null)
  const [selectedTrain, setSelectedTrain] = useState(null)

  const fetchSchedule = async () => {
    try {
      const response = await axios.get('/api/schedule')
      setSchedule(response.data)
    } catch (error) {
      console.error('Error fetching schedule:', error)
    }
  }

  useEffect(() => {
    fetchSchedule()
  }, [])

  const getStatusSummary = () => {
    if (!schedule.length) return { service: 0, standby: 0, ibl: 0 }
    
    return {
      service: schedule.filter(s => s.final_status === 'Service').length,
      standby: schedule.filter(s => s.final_status === 'Standby').length,
      ibl: schedule.filter(s => s.final_status === 'IBL').length
    }
  }

  const summary = getStatusSummary()

  return (
    <div>
      <Hero />
      
      {/* Train Schedule Display */}
      {schedule.length > 0 && (
        <Card style={{ marginTop: 24, marginBottom: 24 }}>
          <Title level={3}>Current Train Schedule</Title>
          
          {/* Status Summary */}
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={8}>
              <Statistic title="Service" value={summary.service} valueStyle={{ color: '#1db954' }} />
            </Col>
            <Col xs={8}>
              <Statistic title="Standby" value={summary.standby} valueStyle={{ color: '#f0ad4e' }} />
            </Col>
            <Col xs={8}>
              <Statistic title="IBL" value={summary.ibl} valueStyle={{ color: '#e55353' }} />
            </Col>
          </Row>
          
          {/* Train Line Display */}
          <div style={{ position: 'relative', padding: '24px 8px 8px 8px', overflowX: 'auto', marginBottom: 24 }}>
            <div style={{ position: 'absolute', left: 0, right: 0, top: 48, height: 6, background: 'linear-gradient(90deg,#9aa7b1,#e5eaef)', borderRadius: 6 }} />
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', minWidth: 'max-content', paddingRight: '16px' }}>
              {schedule.map((train, i) => {
                const color = train.final_status === 'Service' ? '#1db954' : train.final_status === 'Standby' ? '#f0ad4e' : '#e55353'
                return (
                  <motion.div 
                    key={train.train_id} 
                    initial={{ opacity: 0, y: 10 }} 
                    animate={{ opacity: 1, y: 0 }} 
                    transition={{ delay: i*0.01 }} 
                    whileHover={{ scale: 1.06 }} 
                    style={{ cursor: 'pointer', flexShrink: 0 }}
                    onMouseEnter={() => setHoveredTrain(train)}
                    onMouseLeave={() => setHoveredTrain(null)}
                    onClick={() => setSelectedTrain(selectedTrain?.train_id === train.train_id ? null : train)}
                  >
                    <TrainCar id={train.train_id} color={color} />
                  </motion.div>
                )
              })}
            </div>
          </div>

          {/* Train Details */}
          {(hoveredTrain || selectedTrain) && (
            <Card title={`Train Details: ${(hoveredTrain || selectedTrain)?.train_id}`} style={{ marginTop: 16 }}>
              <Row gutter={[16, 16]}>
                <Col xs={12} sm={6}>
                  <Text strong>Status:</Text> <Text style={{ color: hoveredTrain?.final_status === 'Service' ? '#1db954' : hoveredTrain?.final_status === 'Standby' ? '#f0ad4e' : '#e55353' }}>
                    {(hoveredTrain || selectedTrain)?.final_status}
                  </Text>
                </Col>
                <Col xs={12} sm={6}>
                  <Text strong>Failure Risk:</Text> <Text>{(hoveredTrain || selectedTrain)?.predicted_failure_risk ? ((hoveredTrain || selectedTrain)?.predicted_failure_risk * 100).toFixed(1) + '%' : 'N/A'}</Text>
                </Col>
                <Col xs={12} sm={6}>
                  <Text strong>Next Day Mileage:</Text> <Text>{(hoveredTrain || selectedTrain)?.predicted_next_day_mileage ? (hoveredTrain || selectedTrain)?.predicted_next_day_mileage.toFixed(2) + ' km' : 'N/A'}</Text>
                </Col>
                <Col xs={12} sm={6}>
                  <Text strong>Depot:</Text> <Text>{(hoveredTrain || selectedTrain)?.depot}</Text>
                </Col>
                <Col xs={12} sm={6}>
                  <Text strong>Cleaning Slot:</Text> <Text>{(hoveredTrain || selectedTrain)?.cleaning_slot}</Text>
                </Col>
                <Col xs={12} sm={6}>
                  <Text strong>Stabling Position:</Text> <Text>{(hoveredTrain || selectedTrain)?.stabling_position}</Text>
                </Col>
              </Row>
            </Card>
          )}
        </Card>
      )}

      {/* Main Navigation Cards */}
      <div style={{ marginTop: 24 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <Card hoverable title="Operations" extra={<Link to="/dashboard">Open</Link>}>
              Quick glance at train rakes tonight, statuses, and operational KPIs.
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card hoverable title="Scheduling" extra={<Link to="/scheduler">Plan</Link>}>
              Ranked train induction line and predictions for next day operations.
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card hoverable title="Manual Modifications" extra={<Link to="/modifications">Modify</Link>}>
              Modify train assignments and perform what-if analysis scenarios.
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card hoverable title="Data Viewer" extra={<Link to="/data">Explore</Link>}>
              Browse simulation and prediction data across all train records.
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card hoverable title="System Health" extra={<Link to="/dashboard">Monitor</Link>}>
              Latest system status, API health, and operational diagnostics.
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card hoverable title="Analytics" extra={<Link to="/dashboard">Analyze</Link>}>
              Explore train datasets: mileage patterns, failure risks, and status distributions.
            </Card>
          </Col>
        </Row>
      </div>
    </div>
  )
}

function Hero() {
  return (
    <div style={{
      position: 'relative',
      height: '56vh',
      borderRadius: 12,
      overflow: 'hidden',
      backgroundImage: `linear-gradient(rgba(0,0,0,0.4), rgba(0,0,0,0.5)), url(${trainImg})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
    }}>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ color: 'white', padding: 24, flex: 1 }}>
          <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
            <Typography.Text style={{ color: 'rgba(255,255,255,0.9)' }}>Kochi Metro Rail Limited</Typography.Text>
            <div style={{ overflow: 'hidden', whiteSpace: 'nowrap' }}>
              <motion.div
                initial={{ x: '-110%' }}
                animate={{ x: 0 }}
                transition={{ type: 'spring', stiffness: 80, damping: 14 }}
                style={{ fontSize: 40, fontWeight: 800, letterSpacing: 0.5 }}
              >
                KMRL Train Induction & Operations Planner
              </motion.div>
            </div>
            <Typography.Paragraph style={{ marginTop: 8, maxWidth: 780 }}>
              Plan nightly train induction, monitor train health and risks, track maintenance jobs and perform what-if analysis — all in one place.
            </Typography.Paragraph>
            <div style={{ marginTop: 12, display: 'flex', gap: 12 }}>
              <Link to="/scheduler"><Button type="primary">Start Train Scheduling</Button></Link>
              <Link to="/dashboard"><Button>Open Operations Dashboard</Button></Link>
            </div>
          </motion.div>
        </div>
        <div style={{ padding: 24, display: 'flex', alignItems: 'center' }}>
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.3, duration: 0.5 }}
          >
            <img 
              src={metroxLogo} 
              alt="MetroX Logo" 
              style={{ 
                width: 180, 
                height: 180, 
                objectFit: 'contain',
                borderRadius: '50%',
                backgroundColor: 'rgba(255, 255, 255, 0.1)',
                padding: '10px'
              }} 
            />
          </motion.div>
        </div>
      </div>
    </div>
  )
}

function TrainCar({ id, color }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <svg width="80" height="32" viewBox="0 0 80 32">
        <rect x="4" y="8" rx="4" ry="4" width="72" height="16" fill="#0b1e2a" stroke={color} strokeWidth="2" />
        <rect x="10" y="10" rx="2" ry="2" width="18" height="12" fill="#e6f4ff" />
        <rect x="30" y="10" rx="2" ry="2" width="18" height="12" fill="#e6f4ff" />
        <rect x="50" y="10" rx="2" ry="2" width="18" height="12" fill="#e6f4ff" />
        <circle cx="20" cy="26" r="2" fill="#333" />
        <circle cx="60" cy="26" r="2" fill="#333" />
      </svg>
      <div style={{ marginTop: 2, fontSize: 10, fontWeight: 600 }}>{id}</div>
    </div>
  )
}