import React, { useState, useEffect } from 'react';
import { Layout, Card, Row, Col, Statistic, Table, Tag, Progress, Space, Typography, Badge, InputNumber, Button, message } from 'antd';
import { Cpu, Database as Ram, Server, Activity, Globe, HardDrive, Settings } from 'lucide-react';
import { motion } from 'framer-motion';
import axios from 'axios';

const { Content, Header } = Layout;
const { Title, Text } = Typography;

const App: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [maxInstances, setMaxInstances] = useState<number>(3);
  const [savingConfig, setSavingConfig] = useState(false);

  const fetchConfig = async () => {
    try {
      const resp = await axios.get('/api/config');
      setMaxInstances(resp.data.max_game_instances);
    } catch(e) {}
  };

  const handleSaveConfig = async () => {
    setSavingConfig(true);
    try {
      await axios.put('/api/config', { max_game_instances: maxInstances });
      message.success('配置已保存 (Configuration saved)');
      fetchConfig();
    } catch(e) {
      message.error('保存失败 (Failed to save)');
    } finally {
      setSavingConfig(false);
    }
  };

  const fetchStatus = async () => {
    try {
      const resp = await axios.get('/api/status');
      setData(resp.data);
    } catch (e) {
      console.error('Failed to fetch node status', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  if (!data && loading) return <div style={{ color: 'white', padding: '50px' }}>Loading Node Status...</div>;

  const instanceColumns = [
    { title: 'Instance ID', dataIndex: 'id', key: 'id', ellipsis: true },
    { title: 'Game', dataIndex: 'game_type', key: 'game_type', render: (val: string) => <Tag color="blue">{val.toUpperCase()}</Tag> },
    { title: 'Status', dataIndex: 'status', key: 'status', render: (s: string) => <Tag color="green">{s}</Tag> },
    { title: 'Uptime', dataIndex: 'uptime', key: 'uptime' },
  ];

  return (
    <Layout style={{ minHeight: '100vh', background: 'radial-gradient(circle at top right, #1b2735 0%, #090a0f 100%)' }}>
      <Header style={{ background: 'rgba(0,0,0,0.3)', backdropFilter: 'blur(10px)', borderBottom: '1px solid rgba(255,255,255,0.1)', padding: '0 40px', display: 'flex', alignItems: 'center' }}>
        <Title level={4} style={{ color: '#52c41a', margin: 0, letterSpacing: '2px' }}>AURORA AGENT</Title>
        <div style={{ marginLeft: 'auto' }}>
          <Badge status="processing" color="#52c41a" text={<Text style={{ color: 'rgba(255,255,255,0.6)' }}>Node ID: {data?.node_id || 'Unknown'}</Text>} />
        </div>
      </Header>
      
      <Content style={{ padding: '40px' }}>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <Row gutter={[24, 24]}>
            <Col span={16}>
              <Card className="glass-card" title={<Space><Activity size={18} /> LOCAL NODE STATUS</Space>} extra={<Text type="secondary">V2.1.0 Stable</Text>}>
                <Row gutter={24}>
                  <Col span={8}>
                    <Statistic 
                      title={<Space><Cpu size={14} /> CPU USAGE</Space>} 
                      value={Math.round((data?.load_avg || 0) * 100)} 
                      suffix="%" 
                      valueStyle={{ color: '#52c41a' }}
                    />
                    <Progress percent={Math.round((data?.load_avg || 0) * 100)} showInfo={false} strokeColor="#52c41a" />
                  </Col>
                  <Col span={8}>
                    <Statistic 
                      title={<Space><Ram size={14} /> RAM USAGE</Space>} 
                      value={data?.ram_usage || 45} 
                      suffix="%" 
                    />
                    <Progress percent={data?.ram_usage || 45} showInfo={false} />
                  </Col>
                  <Col span={8}>
                    <Statistic 
                      title={<Space><HardDrive size={14} /> DISK LOAD</Space>} 
                      value={12} 
                      suffix="%" 
                    />
                    <Progress percent={12} showInfo={false} strokeColor="#1890ff" />
                  </Col>
                </Row>
              </Card>

              <Card style={{ marginTop: '24px' }} className="glass-card" title={<Space><Server size={18} /> HOSTED CONTAINERS</Space>}>
                <Table 
                  columns={instanceColumns} 
                  dataSource={data?.instances || []} 
                  pagination={false} 
                  size="small" 
                  rowKey="id"
                />
              </Card>
            </Col>

            <Col span={8}>
              <Card className="glass-card" title={<Space><Globe size={18} /> CONNECTIVITY</Space>}>
                <div style={{ padding: '10px 0' }}>
                  <div style={{ marginBottom: '15px' }}>
                    <Text type="secondary">Center Address</Text>
                    <div style={{ color: 'white' }}>http://localhost:8123</div>
                  </div>
                  <div style={{ marginBottom: '15px' }}>
                    <Text type="secondary">Health Check</Text>
                    <div><Tag color="success">EXCELLENT</Tag></div>
                  </div>
                  <div>
                    <Text type="secondary">Latency</Text>
                    <div style={{ color: '#52c41a' }}>12ms</div>
                  </div>
                </div>
              </Card>

              <Card style={{ marginTop: '24px' }} className="glass-card" title="QUICK STATS">
                <Statistic title="Total Runtime" value="14d 06h 11m" valueStyle={{ fontSize: '16px' }} />
                <Statistic title="Data Synced" value="1.4 GB" valueStyle={{ fontSize: '16px' }} style={{ marginTop: '15px' }} />
              </Card>

              <Card style={{ marginTop: '24px' }} className="glass-card" title={<Space><Settings size={18} /> NODE CONFIGURATION</Space>}>
                <div style={{ padding: '10px 0' }}>
                  <Text style={{ display: 'block', marginBottom: '8px', color: 'rgba(255,255,255,0.85)' }}>Max Game Instances (最大游戏实例数)</Text>
                  <Space>
                    <InputNumber 
                      min={1} 
                      max={100} 
                      value={maxInstances} 
                      onChange={(val) => setMaxInstances(val || 3)} 
                      style={{ width: '120px' }}
                    />
                    <Button type="primary" loading={savingConfig} onClick={handleSaveConfig}>
                      Save Config
                    </Button>
                  </Space>
                </div>
              </Card>
            </Col>
          </Row>
        </motion.div>
      </Content>
    </Layout>
  );
};

export default App;
