import { useState, useEffect } from 'react'
import { Typography, Card, Row, Col, Statistic, Progress, Table, Tag, Alert, Button } from 'antd'
import { CheckCircleOutlined, ExclamationCircleOutlined, WarningOutlined, InfoCircleOutlined, ReloadOutlined } from '@ant-design/icons'
import { motion } from 'framer-motion'
import axios from 'axios'

const { Title, Text } = Typography

export default function Dashboard() {
  const [predictions, setPredictions] = useState([])
  const [simulatedData, setSimulatedData] = useState([])
  const [fleetAnalytics, setFleetAnalytics] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [predictionsRes, simulatedRes, analyticsRes] = await Promise.all([
          axios.get('/api/data/predictions'),
          axios.get('/api/data/simulated'),
          axios.get('/api/fleet-analytics').catch(() => ({ data: { report: null } }))
        ])
        setPredictions(predictionsRes.data)
        setSimulatedData(simulatedRes.data)
        setFleetAnalytics(analyticsRes.data.report)
      } catch (error) {
        console.error('Error fetching data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    
    // Set up polling for alerts every 30 seconds
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

  const getFleetSummary = () => {
    if (!predictions.length) return null

    const service = predictions.filter(p => p.final_status === 'Service').length
    const standby = predictions.filter(p => p.final_status === 'Standby').length
    const ibl = predictions.filter(p => p.final_status === 'IBL').length
    const total = predictions.length

    return { service, standby, ibl, total }
  }

  const getRiskAnalysis = () => {
    if (!predictions.length) return null

    const highRisk = predictions.filter(p => p.predicted_failure_risk > 0.3).length
    const mediumRisk = predictions.filter(p => p.predicted_failure_risk > 0.1 && p.predicted_failure_risk <= 0.3).length
    const lowRisk = predictions.filter(p => p.predicted_failure_risk <= 0.1).length

    return { highRisk, mediumRisk, lowRisk }
  }

  const getMaintenanceAlerts = () => {
    if (!simulatedData.length) return []

    return simulatedData.filter(train => 
      train.job_critical_count > 0 || 
      train.rs_days_from_plan <= 0 || 
      train.sig_days_from_plan <= 0 || 
      train.tel_days_from_plan <= 0
    )
  }

  const fleetSummary = getFleetSummary()
  const riskAnalysis = getRiskAnalysis()
  const maintenanceAlerts = getMaintenanceAlerts()

  if (loading) {
    return <div>Loading...</div>
  }

  return (
    <div>
      <Title level={2}>📊 System Dashboard</Title>

      {/* Fleet Overview */}
      {fleetSummary && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={6}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              <Card>
                <Statistic
                  title="Service Trains"
                  value={fleetSummary.service}
                  suffix={`/ ${fleetSummary.total}`}
                  valueStyle={{ color: '#1db954' }}
                  prefix={<CheckCircleOutlined />}
                />
                <Progress 
                  percent={(fleetSummary.service / fleetSummary.total) * 100} 
                  strokeColor="#1db954"
                  showInfo={false}
                  size="small"
                />
              </Card>
            </motion.div>
          </Col>
          <Col xs={24} sm={6}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
            >
              <Card>
                <Statistic
                  title="Standby Trains"
                  value={fleetSummary.standby}
                  suffix={`/ ${fleetSummary.total}`}
                  valueStyle={{ color: '#f0ad4e' }}
                  prefix={<WarningOutlined />}
                />
                <Progress 
                  percent={(fleetSummary.standby / fleetSummary.total) * 100} 
                  strokeColor="#f0ad4e"
                  showInfo={false}
                  size="small"
                />
              </Card>
            </motion.div>
          </Col>
          <Col xs={24} sm={6}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
            >
              <Card>
                <Statistic
                  title="IBL Trains"
                  value={fleetSummary.ibl}
                  suffix={`/ ${fleetSummary.total}`}
                  valueStyle={{ color: '#e55353' }}
                  prefix={<ExclamationCircleOutlined />}
                />
                <Progress 
                  percent={(fleetSummary.ibl / fleetSummary.total) * 100} 
                  strokeColor="#e55353"
                  showInfo={false}
                  size="small"
                />
              </Card>
            </motion.div>
          </Col>
          <Col xs={24} sm={6}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
            >
              <Card>
                <Statistic
                  title="Fleet Health"
                  value={Math.round(((fleetSummary.service + fleetSummary.standby) / fleetSummary.total) * 100)}
                  suffix="%"
                  valueStyle={{ color: '#1890ff' }}
                  prefix={<InfoCircleOutlined />}
                />
                <Progress 
                  percent={((fleetSummary.service + fleetSummary.standby) / fleetSummary.total) * 100} 
                  strokeColor="#1890ff"
                  showInfo={false}
                  size="small"
                />
              </Card>
            </motion.div>
          </Col>
        </Row>
      )}

      {/* Risk Analysis */}
      {riskAnalysis && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} md={8}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
            >
              <Card>
                <Statistic
                  title="High Risk Trains"
                  value={riskAnalysis.highRisk}
                  valueStyle={{ color: '#e55353' }}
                  prefix={<ExclamationCircleOutlined />}
                />
                <Text type="secondary">Failure risk &gt; 30%</Text>
              </Card>
            </motion.div>
          </Col>
          <Col xs={24} md={8}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.5 }}
            >
              <Card>
                <Statistic
                  title="Medium Risk Trains"
                  value={riskAnalysis.mediumRisk}
                  valueStyle={{ color: '#f0ad4e' }}
                  prefix={<WarningOutlined />}
                />
                <Text type="secondary">Failure risk 10-30%</Text>
              </Card>
            </motion.div>
          </Col>
          <Col xs={24} md={8}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.6 }}
            >
              <Card>
                <Statistic
                  title="Low Risk Trains"
                  value={riskAnalysis.lowRisk}
                  valueStyle={{ color: '#1db954' }}
                  prefix={<CheckCircleOutlined />}
                />
                <Text type="secondary">Failure risk &lt; 10%</Text>
              </Card>
            </motion.div>
          </Col>
        </Row>
      )}



      {/* Maintenance Alerts */}
      {maintenanceAlerts.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.8 }}
          style={{ marginBottom: 24 }}
        >
          <Card>
            <Title level={4}>🔧 Critical Maintenance Alerts</Title>
            <Table
              dataSource={maintenanceAlerts}
              columns={[
                {
                  title: 'Train ID',
                  dataIndex: 'train_id',
                  key: 'train_id',
                },
                {
                  title: 'Critical Jobs',
                  dataIndex: 'job_critical_count',
                  key: 'job_critical_count',
                  render: (value) => value > 0 ? <Tag color="red">{value}</Tag> : <Tag color="green">0</Tag>
                },
                {
                  title: 'RS Days',
                  dataIndex: 'rs_days_from_plan',
                  key: 'rs_days_from_plan',
                  render: (value) => value <= 0 ? <Tag color="red">{value}</Tag> : <Tag color="green">{value}</Tag>
                },
                {
                  title: 'SIG Days',
                  dataIndex: 'sig_days_from_plan',
                  key: 'sig_days_from_plan',
                  render: (value) => value <= 0 ? <Tag color="red">{value}</Tag> : <Tag color="green">{value}</Tag>
                },
                {
                  title: 'TEL Days',
                  dataIndex: 'tel_days_from_plan',
                  key: 'tel_days_from_plan',
                  render: (value) => value <= 0 ? <Tag color="red">{value}</Tag> : <Tag color="green">{value}</Tag>
                },
              ]}
              rowKey="train_id"
              pagination={false}
              size="small"
            />
          </Card>
        </motion.div>
      )}

      {/* KMRL Fleet Analytics Report */}
      {fleetAnalytics && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.8 }}
          style={{ marginBottom: 24 }}
        >
          <Card>
            <Title level={4}>🚆 KMRL Metro Fleet Analytics Report</Title>
            
            {/* Fleet Health Index */}
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
              <Col xs={24} md={8}>
                <Card>
                  <Statistic
                    title="Fleet Health Index"
                    value={fleetAnalytics['Fleet Health Index']}
                    suffix="/ 100"
                    valueStyle={{ 
                      color: fleetAnalytics['Fleet Health Index'] >= 80 ? '#1db954' : 
                             fleetAnalytics['Fleet Health Index'] >= 60 ? '#f0ad4e' : '#e55353' 
                    }}
                    prefix={<InfoCircleOutlined />}
                  />
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card>
                  <Statistic
                    title="Revenue Impact"
                    value={`₹${fleetAnalytics['Revenue Impact']?.potential_loss?.toLocaleString() || 0}`}
                    valueStyle={{ color: '#1890ff' }}
                    prefix={<CheckCircleOutlined />}
                  />
                  <Text type="secondary">Potential daily loss</Text>
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card>
                  <Statistic
                    title="Out of Service"
                    value={fleetAnalytics['Revenue Impact']?.out_of_service || 0}
                    valueStyle={{ color: '#e55353' }}
                    prefix={<ExclamationCircleOutlined />}
                  />
                  <Text type="secondary">IBL trains</Text>
                </Card>
              </Col>
            </Row>

            {/* Resource Optimization */}
            {fleetAnalytics['Resource Optimization Suggestions'] && fleetAnalytics['Resource Optimization Suggestions'].length > 0 && (
              <div style={{ marginBottom: 24 }}>
                <Title level={5}>🔧 Resource Optimization Suggestions</Title>
                <Alert
                  message="Optimization Opportunities"
                  description={
                    <ul style={{ margin: 0, paddingLeft: 20 }}>
                      {fleetAnalytics['Resource Optimization Suggestions'].map((suggestion, index) => (
                        <li key={index}>{suggestion}</li>
                      ))}
                    </ul>
                  }
                  type="info"
                  showIcon
                />
              </div>
            )}

            {/* Dynamic Route Assignment */}
            {fleetAnalytics['Dynamic Route Assignment'] && fleetAnalytics['Dynamic Route Assignment'].length > 0 && (
              <div style={{ marginBottom: 24 }}>
                <Title level={5}>🚇 Dynamic Route Assignment</Title>
                <Table
                  dataSource={fleetAnalytics['Dynamic Route Assignment']}
                  columns={[
                    {
                      title: 'Train ID',
                      dataIndex: 'train_id',
                      key: 'train_id',
                    },
                    {
                      title: 'Assigned Route',
                      dataIndex: 'assigned_route',
                      key: 'assigned_route',
                      render: (route) => <Tag color="blue">{route}</Tag>
                    },
                    {
                      title: 'Reliability',
                      dataIndex: 'reliability',
                      key: 'reliability',
                      render: (value) => `${(value * 100).toFixed(1)}%`
                    },
                  ]}
                  rowKey="train_id"
                  pagination={false}
                  size="small"
                />
              </div>
            )}

            {/* Energy Efficiency */}
            {fleetAnalytics['Energy Efficiency'] && fleetAnalytics['Energy Efficiency'].length > 0 && (
              <div style={{ marginBottom: 24 }}>
                <Title level={5}>⚡ Energy Efficiency</Title>
                <Table
                  dataSource={fleetAnalytics['Energy Efficiency'].slice(0, 10)} // Show top 10
                  columns={[
                    {
                      title: 'Train ID',
                      dataIndex: 'train_id',
                      key: 'train_id',
                    },
                    {
                      title: 'kWh/100km',
                      dataIndex: 'kWh/100km',
                      key: 'kWh/100km',
                    },
                    {
                      title: 'Rating',
                      dataIndex: 'rating',
                      key: 'rating',
                      render: (rating) => {
                        const colors = {
                          'Excellent': 'green',
                          'Good': 'blue',
                          'Poor': 'red'
                        }
                        return <Tag color={colors[rating] || 'default'}>{rating}</Tag>
                      }
                    },
                    {
                      title: 'Main Issue',
                      dataIndex: 'main_issue',
                      key: 'main_issue',
                    },
                  ]}
                  rowKey="train_id"
                  pagination={false}
                  size="small"
                />
              </div>
            )}

            {/* Passenger Experience */}
            {fleetAnalytics['Passenger Experience'] && fleetAnalytics['Passenger Experience'].length > 0 && (
              <div style={{ marginBottom: 24 }}>
                <Title level={5}>👥 Passenger Experience</Title>
                <Table
                  dataSource={fleetAnalytics['Passenger Experience'].slice(0, 10)} // Show top 10
                  columns={[
                    {
                      title: 'Train ID',
                      dataIndex: 'train_id',
                      key: 'train_id',
                    },
                    {
                      title: 'Score',
                      dataIndex: 'score',
                      key: 'score',
                      render: (score) => `${score}/100`
                    },
                    {
                      title: 'Rating',
                      dataIndex: 'rating',
                      key: 'rating',
                      render: (rating) => {
                        const colors = {
                          'Excellent': 'green',
                          'Good': 'blue',
                          'Fair': 'orange',
                          'Poor': 'red'
                        }
                        return <Tag color={colors[rating] || 'default'}>{rating}</Tag>
                      }
                    },
                    {
                      title: 'Factors',
                      dataIndex: 'factors',
                      key: 'factors',
                      render: (factors) => factors.join(', ')
                    },
                  ]}
                  rowKey="train_id"
                  pagination={false}
                  size="small"
                />
              </div>
            )}

            {/* Intelligent Maintenance Schedule */}
            {fleetAnalytics['Intelligent Maintenance Schedule'] && Object.keys(fleetAnalytics['Intelligent Maintenance Schedule']).length > 0 && (
              <div style={{ marginBottom: 24 }}>
                <Title level={5}>🔧 Intelligent Maintenance Schedule</Title>
                <Table
                  dataSource={Object.entries(fleetAnalytics['Intelligent Maintenance Schedule']).slice(0, 10).map(([train_id, schedule]) => ({
                    train_id,
                    ...schedule
                  }))}
                  columns={[
                    {
                      title: 'Train ID',
                      dataIndex: 'train_id',
                      key: 'train_id',
                    },
                    {
                      title: 'Priority',
                      dataIndex: 'priority',
                      key: 'priority',
                      render: (priority) => priority.toFixed(1)
                    },
                    {
                      title: 'Urgency',
                      dataIndex: 'urgency',
                      key: 'urgency',
                      render: (urgency) => {
                        const colors = {
                          'IMMEDIATE': 'red',
                          'HIGH': 'orange',
                          'MEDIUM': 'blue',
                          'LOW': 'green'
                        }
                        return <Tag color={colors[urgency] || 'default'}>{urgency}</Tag>
                      }
                    },
                    {
                      title: 'Types',
                      dataIndex: 'types',
                      key: 'types',
                      render: (types) => types.join(', ')
                    },
                    {
                      title: 'Est. Hours',
                      dataIndex: 'est_hours',
                      key: 'est_hours',
                    },
                  ]}
                  rowKey="train_id"
                  pagination={false}
                  size="small"
                />
              </div>
            )}

            {/* Fleet Allocation Justification */}
            {fleetAnalytics['Fleet Allocation Justification'] && (
              <div>
                <Title level={5}>📊 Fleet Allocation Justification</Title>
                <Row gutter={[16, 16]}>
                  <Col xs={12} sm={6}>
                    <Statistic
                      title="Total Fleet"
                      value={fleetAnalytics['Fleet Allocation Justification'].fleet_size}
                      valueStyle={{ color: '#1890ff' }}
                    />
                  </Col>
                  <Col xs={12} sm={6}>
                    <Statistic
                      title="Service Trains"
                      value={fleetAnalytics['Fleet Allocation Justification'].min_service_trains}
                      valueStyle={{ color: '#1db954' }}
                    />
                  </Col>
                  <Col xs={12} sm={6}>
                    <Statistic
                      title="Standby Trains"
                      value={fleetAnalytics['Fleet Allocation Justification'].min_standby_trains}
                      valueStyle={{ color: '#f0ad4e' }}
                    />
                  </Col>
                  <Col xs={12} sm={6}>
                    <Statistic
                      title="Expected Revenue"
                      value={`₹${fleetAnalytics['Fleet Allocation Justification'].expected_revenue?.toLocaleString() || 0}`}
                      valueStyle={{ color: '#52c41a' }}
                    />
                  </Col>
                </Row>
                <Alert
                  message="Allocation Note"
                  description={fleetAnalytics['Fleet Allocation Justification'].note}
                  type="info"
                  showIcon
                  style={{ marginTop: 16 }}
                />
              </div>
            )}
          </Card>
        </motion.div>
      )}

      {/* System Status */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.9 }}
      >
        <Card>
          <Title level={4}>System Status</Title>
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Alert
                message="Data Pipeline"
                description="Simulation and prediction scripts are ready"
                type="success"
                showIcon
              />
            </Col>
            <Col xs={24} md={12}>
              <Alert
                message="ML Models"
                description="Status classifier, failure regressor, and mileage regressor loaded"
                type="success"
                showIcon
              />
            </Col>
          </Row>
        </Card>
      </motion.div>
    </div>
  )
}
