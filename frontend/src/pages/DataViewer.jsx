import { useState, useEffect, useMemo } from 'react'
import { Card, Row, Col, Table, Tag, Typography, Space, Select, Badge, Statistic, Divider, Button } from 'antd'
import ReactECharts from 'echarts-for-react'
import { motion } from 'framer-motion'
import axios from 'axios'

const { Title, Text } = Typography

export default function DataViewer() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('branding')

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const response = await axios.get('/api/schedule')
      setData(response.data)
    } catch (error) {
      console.error('Error fetching data:', error)
    } finally {
      setLoading(false)
    }
  }

  // Branding Data Processing
  const brandingData = useMemo(() => {
    const advertisers = ['KMRL Tourism', 'CocoFizz', 'Kerala Gold', 'GreenBank', 'DosaKing', 'TechCorp', 'HealthPlus', 'EcoClean']
    return data.map((train, i) => ({
      key: i,
      advertiser: advertisers[i % advertisers.length],
      train_id: train.train_id,
      required_hours: Number(train.branding_req_hours || 0),
      allocated_hours: Number(train.branding_alloc_hours || 0),
      reach: Math.round((Number(train.mileage_km || 0) / 1000) * (1 + (i % 3) * 0.2) * 100) / 100,
      status: train.final_status,
      depot: train.depot
    }))
  }, [data])

  // Job Cards Data Processing
  const jobCardsData = useMemo(() => {
    return data
      .map((train, i) => ({
        key: i,
        train_id: train.train_id,
        depot: train.depot,
        raw_open: Number(train.job_open_count || 0),
        raw_critical: Number(train.job_critical_count || 0),
        last_maintenance_date: train.last_maintenance_date,
        rs_days: train.rs_days_from_plan,
        sig_days: train.sig_days_from_plan,
        tel_days: train.tel_days_from_plan,
        failure_risk: train.predicted_failure_risk
      }))
      .map(train => ({
        ...train,
        open: Math.max(train.raw_open, train.raw_critical),
        critical: train.raw_critical,
        inconsistent: train.raw_critical > train.raw_open,
        maintenance_overdue: train.rs_days <= 0 || train.sig_days <= 0 || train.tel_days <= 0
      }))
      .filter(train => train.open > 0 || train.critical > 0 || train.maintenance_overdue)
  }, [data])

  // EDA Data Processing
  const edaData = useMemo(() => {
    return data.map(train => ({
      train_id: train.train_id,
      mileage_km: Number(train.mileage_km || 0),
      predicted_failure_risk: Number(train.predicted_failure_risk || 0),
      final_status: train.final_status,
      predicted_status: train.predicted_status,
      bogie_wear_index: Number(train.bogie_wear_index || 0),
      depot: train.depot,
      hvac_alert: train.hvac_alert,
      iot_temp_avg_c: Number(train.iot_temp_avg_c || 0)
    }))
  }, [data])

  // Chart Options
  const reachBarOption = {
    tooltip: {},
    xAxis: { 
      type: 'category', 
      data: [...new Set(brandingData.map(d => d.advertiser))],
      axisLabel: { rotate: 45 }
    },
    yAxis: { type: 'value', name: 'Reach (k est.)' },
    series: [{
      type: 'bar',
      data: [...new Set(brandingData.map(d => d.advertiser))].map(adv => 
        brandingData.filter(d => d.advertiser === adv).reduce((sum, d) => sum + d.reach, 0)
      ),
      itemStyle: { color: '#1890ff' }
    }]
  }

  const statusPieOption = {
    tooltip: {},
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: Object.entries(
        edaData.reduce((acc, train) => {
          acc[train.final_status] = (acc[train.final_status] || 0) + 1
          return acc
        }, {})
      ).map(([name, value]) => ({ name, value }))
    }]
  }

  const mileageBarOption = {
    tooltip: {},
    xAxis: { 
      type: 'category', 
      data: edaData.map(d => d.train_id),
      axisLabel: { rotate: 45 }
    },
    yAxis: { type: 'value', name: 'Mileage (km)' },
    series: [{
      type: 'bar',
      data: edaData.map(d => d.mileage_km),
      itemStyle: { color: '#52c41a' }
    }]
  }

  const riskVsMileageOption = {
    tooltip: { 
      trigger: 'item', 
      formatter: (params) => `Train ${params.data[2]}<br/>Mileage: ${params.data[0]} km<br/>Risk: ${(params.data[1] * 100).toFixed(1)}%` 
    },
    xAxis: { type: 'value', name: 'Mileage (km)' },
    yAxis: { type: 'value', name: 'Failure Risk' },
    series: [{
      type: 'scatter',
      data: edaData.map(d => [d.mileage_km, d.predicted_failure_risk, d.train_id]),
      itemStyle: { color: '#ff4d4f' }
    }]
  }

  const maintenanceStatusOption = {
    tooltip: {},
    xAxis: { 
      type: 'category', 
      data: ['RS', 'SIG', 'TEL'],
      name: 'Maintenance Type'
    },
    yAxis: { type: 'value', name: 'Days from Plan' },
    series: [{
      type: 'bar',
      data: [
        edaData.reduce((sum, d) => sum + (d.rs_days_from_plan || 0), 0) / edaData.length,
        edaData.reduce((sum, d) => sum + (d.sig_days_from_plan || 0), 0) / edaData.length,
        edaData.reduce((sum, d) => sum + (d.tel_days_from_plan || 0), 0) / edaData.length
      ],
      itemStyle: { color: '#faad14' }
    }]
  }

  const brandingAllocationOption = {
    tooltip: {},
    xAxis: { 
      type: 'category', 
      data: brandingData.map(d => d.train_id),
      axisLabel: { rotate: 45 }
    },
    yAxis: { type: 'value', name: 'Hours' },
    series: [
      {
        name: 'Required',
        type: 'bar',
        data: brandingData.map(d => d.required_hours),
        itemStyle: { color: '#ff7875' }
      },
      {
        name: 'Allocated',
        type: 'bar',
        data: brandingData.map(d => d.allocated_hours),
        itemStyle: { color: '#52c41a' }
      }
    ]
  }

  const renderBrandingSection = () => (
    <div>
      <Title level={3}>📊 Branding Analysis</Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
            <Card title="Estimated Reach by Advertiser">
              <ReactECharts style={{ height: 320 }} option={reachBarOption} />
            </Card>
          </motion.div>
        </Col>
        <Col xs={24} md={12}>
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <Card title="Branding Allocation vs Requirement">
              <ReactECharts style={{ height: 320 }} option={brandingAllocationOption} />
            </Card>
          </motion.div>
        </Col>
        <Col xs={24}>
          <Card title="Branding Details">
            <Table
              size="small"
              dataSource={brandingData}
              columns={[
                { title: 'Advertiser', dataIndex: 'advertiser' },
                { title: 'Train', dataIndex: 'train_id' },
                { title: 'Status', dataIndex: 'status', render: (status) => {
                  const color = status === 'Service' ? 'green' : status === 'Standby' ? 'orange' : 'red'
                  return <Tag color={color}>{status}</Tag>
                }},
                { title: 'Depot', dataIndex: 'depot' },
                { title: 'Required (h)', dataIndex: 'required_hours' },
                { title: 'Allocated (h)', dataIndex: 'allocated_hours',
                  render: (v, r) => {
                    const ok = (v || 0) >= (r.required_hours || 0)
                    return <Tag color={ok ? 'green' : 'volcano'}>{v}</Tag>
                  }
                },
                { title: 'Reach (k est.)', dataIndex: 'reach' },
              ]}
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )

  const renderJobCardsSection = () => (
    <div>
      <Title level={3}>🔧 Job Cards & Maintenance</Title>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={8}>
          <Card>
            <Statistic
              title="Total Open Jobs"
              value={jobCardsData.reduce((sum, d) => sum + d.open, 0)}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={8}>
          <Card>
            <Statistic
              title="Critical Jobs"
              value={jobCardsData.reduce((sum, d) => sum + d.critical, 0)}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col xs={8}>
          <Card>
            <Statistic
              title="Overdue Maintenance"
              value={jobCardsData.filter(d => d.maintenance_overdue).length}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card title="Maintenance Status Overview">
            <ReactECharts style={{ height: 320 }} option={maintenanceStatusOption} />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="Job Cards Summary">
            <Table
              size="small"
              dataSource={jobCardsData}
              columns={[
                { title: 'Train', dataIndex: 'train_id' },
                { title: 'Depot', dataIndex: 'depot' },
                { title: 'Open Jobs', dataIndex: 'open', render: (v, r) => 
                  r.inconsistent ? <Badge color="orange" text={v} /> : v 
                },
                { title: 'Critical', dataIndex: 'critical', render: v => 
                  <Tag color={v > 0 ? 'volcano' : 'default'}>{v}</Tag> 
                },
                { title: 'RS Days', dataIndex: 'rs_days', render: v => 
                  <Tag color={v <= 0 ? 'red' : v <= 7 ? 'orange' : 'green'}>{v}</Tag>
                },
                { title: 'SIG Days', dataIndex: 'sig_days', render: v => 
                  <Tag color={v <= 0 ? 'red' : v <= 7 ? 'orange' : 'green'}>{v}</Tag>
                },
                { title: 'TEL Days', dataIndex: 'tel_days', render: v => 
                  <Tag color={v <= 0 ? 'red' : v <= 7 ? 'orange' : 'green'}>{v}</Tag>
                },
                { title: 'Last Maintenance', dataIndex: 'last_maintenance_date' },
              ]}
              pagination={{ pageSize: 8 }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )

  const renderEDASection = () => (
    <div>
      <Title level={3}>📈 Exploratory Data Analysis</Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card title="Mileage by Train">
            <ReactECharts style={{ height: 320 }} option={mileageBarOption} />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="Status Distribution">
            <ReactECharts style={{ height: 320 }} option={statusPieOption} />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="Failure Risk vs Mileage">
            <ReactECharts style={{ height: 320 }} option={riskVsMileageOption} />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="Fleet Health Overview">
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic
                  title="Avg Mileage"
                  value={edaData.reduce((sum, d) => sum + d.mileage_km, 0) / edaData.length}
                  precision={0}
                  suffix="km"
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Avg Failure Risk"
                  value={edaData.reduce((sum, d) => sum + d.predicted_failure_risk, 0) / edaData.length * 100}
                  precision={1}
                  suffix="%"
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="HVAC Alerts"
                  value={edaData.filter(d => d.hvac_alert).length}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Avg Temperature"
                  value={edaData.reduce((sum, d) => sum + d.iot_temp_avg_c, 0) / edaData.length}
                  precision={1}
                  suffix="°C"
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  )

  return (
    <div>
      <div style={{ textAlign: 'center', marginBottom: 32 }}>
        <Title level={2}>📊 Data Viewer & Analytics</Title>
        <Text type="secondary">Comprehensive analysis of train data, branding, job cards, and fleet health</Text>
      </div>

      {/* Tab Navigation */}
      <Card style={{ marginBottom: 24 }}>
        <Space size="large">
          <Button 
            type={activeTab === 'branding' ? 'primary' : 'default'}
            onClick={() => setActiveTab('branding')}
          >
            📊 Branding
          </Button>
          <Button 
            type={activeTab === 'jobcards' ? 'primary' : 'default'}
            onClick={() => setActiveTab('jobcards')}
          >
            🔧 Job Cards
          </Button>
          <Button 
            type={activeTab === 'eda' ? 'primary' : 'default'}
            onClick={() => setActiveTab('eda')}
          >
            📈 EDA
          </Button>
        </Space>
      </Card>

      {/* Content Sections */}
      {activeTab === 'branding' && renderBrandingSection()}
      {activeTab === 'jobcards' && renderJobCardsSection()}
      {activeTab === 'eda' && renderEDASection()}

      {/* Refresh Button */}
      <div style={{ textAlign: 'center', marginTop: 32 }}>
        <Button 
          type="primary" 
          size="large"
          loading={loading}
          onClick={fetchData}
        >
          🔄 Refresh Data
        </Button>
      </div>
    </div>
  )
}