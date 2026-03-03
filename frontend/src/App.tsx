import React, { useState, useEffect } from 'react';
import { Layout, Menu, Typography, Space, Card, Row, Col, Statistic, Table, Tag, Button, Progress, message, Modal, Form, Input, Select } from 'antd';
import { 
  BarChart3, 
  Server, 
  Gamepad2, 
  Activity, 
  Settings, 
  Terminal,
  Plus
} from 'lucide-react';
import { motion } from 'framer-motion';
import { getNodes, getInstances, deployGame, stopGame } from './services/api';

const { Content, Sider } = Layout;
const { Title, Text } = Typography;

const App: React.FC = () => {
  const [nodes, setNodes] = useState<any[]>([]);
  const [instances, setInstances] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form] = Form.useForm();

  const openDeployModal = (nodeId?: string) => {
    form.resetFields();
    if (nodeId) {
      form.setFieldsValue({ node_id: nodeId });
    }
    setIsModalOpen(true);
  };

  const fetchData = async () => {
    try {
      const [nodesData, instancesData] = await Promise.all([
        getNodes(),
        getInstances()
      ]);
      setNodes(Object.values(nodesData));
      setInstances(Object.values(instancesData));
    } catch (error) {
      console.error('Failed to fetch data', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleDeploy = async (values: any) => {
    try {
      await deployGame(values.game_type, values.owner_id, values.save_path, values.node_id);
      message.success('Deployment queued');
      setIsModalOpen(false);
      form.resetFields();
      fetchData();
    } catch (error) {
      message.error('Failed to deploy game');
    }
  };

  const handleStop = async (id: string) => {
    try {
      await stopGame(id);
      message.success('Stop task issued');
      fetchData();
    } catch (error) {
      message.error('Failed to stop instance');
    }
  };

  const nodeColumns = [
    { title: 'Status', dataIndex: 'status', key: 'status', render: (status: string) => <Tag color={status === 'ONLINE' ? 'success' : 'error'}>{status}</Tag> },
    { title: 'Node Name', dataIndex: 'hostname', key: 'hostname' },
    { title: 'IP', dataIndex: 'ip', key: 'ip' },
    { title: 'CPU Load', dataIndex: 'load_avg', key: 'load_avg', render: (val: number) => <Progress percent={Math.round((val || 0) * 100)} size="small" strokeColor="#1890ff" /> },
    { title: 'Instances', dataIndex: 'running_instances', key: 'running_instances' },
    { title: 'Last Seen', dataIndex: 'last_seen', key: 'last_seen', render: (ts: string) => new Date(ts).toLocaleTimeString() },
    { title: 'Actions', key: 'actions', render: (_: any, record: any) => (
      <Button 
        type="link" 
        size="small" 
        disabled={record.status !== 'ONLINE'} 
        icon={<Plus size={14} />} 
        onClick={() => openDeployModal(record.id)}
      >
        Deploy
      </Button>
    )},
  ];

  const instanceColumns = [
    { title: 'Game', dataIndex: 'game_type', key: 'game_type', render: (val: string) => <Tag color="blue">{val.toUpperCase()}</Tag> },
    { title: 'Instance ID', dataIndex: 'id', key: 'id', ellipsis: true },
    { title: 'Node', dataIndex: 'node_id', key: 'node_id', ellipsis: true },
    { title: 'Status', dataIndex: 'status', key: 'status', render: (status: string) => <Tag color={status === 'RUNNING' ? 'green' : 'orange'}>{status}</Tag> },
    { title: 'Actions', key: 'actions', render: (_: any, record: any) => (
      <Button type="link" danger size="small" onClick={() => handleStop(record.id)}>Stop</Button>
    )},
  ];

  return (
    <Layout style={{ minHeight: '100vh', background: 'transparent' }}>
      <Sider width={240} className="glass-card" style={{ margin: '16px', height: 'calc(100vh - 32px)' }}>
        <div style={{ padding: '24px', textAlign: 'center' }}>
          <Title level={3} style={{ color: '#1890ff', margin: 0, letterSpacing: '2px' }}>AURORA</Title>
          <Text type="secondary" style={{ fontSize: '10px' }}>CENTER DASHBOARD</Text>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          defaultSelectedKeys={['1']}
          style={{ background: 'transparent', border: 'none' }}
          items={[
            { key: '1', icon: <BarChart3 size={18} />, label: 'Dashboard' },
            { key: '2', icon: <Server size={18} />, label: 'Infrastructure' },
            { key: '3', icon: <Gamepad2 size={18} />, label: 'Active Games' },
            { key: '4', icon: <Terminal size={18} />, label: 'System Logs' },
            { key: '5', icon: <Settings size={18} />, label: 'Global Settings' },
          ]}
        />
      </Sider>
      
      <Layout style={{ background: 'transparent' }}>
        <Content style={{ padding: '24px', overflowY: 'auto' }}>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
              <Title level={2} style={{ margin: 0 }}>Cluster Overview</Title>
              <Button type="primary" icon={<Plus size={16} />} onClick={() => openDeployModal()}>Deploy New Game</Button>
            </div>
            
            <Row gutter={[16, 16]}>
              <Col span={6}><Card className="glass-card"><Statistic title="Total Nodes" value={nodes.length} /></Card></Col>
              <Col span={6}><Card className="glass-card"><Statistic title="Online Nodes" value={nodes.filter(n => n.status === 'ONLINE').length} /></Card></Col>
              <Col span={6}><Card className="glass-card"><Statistic title="Running Games" value={instances.length} /></Card></Col>
              <Col span={6}><Card className="glass-card"><Statistic title="Total Load" value={nodes.reduce((acc, n) => acc + (n.load_avg || 0), 0).toFixed(2)} suffix="Avg" /></Card></Col>
            </Row>

            <Card style={{ marginTop: '24px' }} className="glass-card" title={<Space><Server size={18} /> Compute Nodes</Space>}>
              <Table columns={nodeColumns} dataSource={nodes} rowKey="id" pagination={false} size="small" loading={loading} />
            </Card>

            <Card style={{ marginTop: '24px' }} className="glass-card" title={<Space><Gamepad2 size={18} /> Active Game Instances</Space>}>
              <Table columns={instanceColumns} dataSource={instances} rowKey="id" pagination={false} size="small" loading={loading} />
            </Card>
          </motion.div>
        </Content>
      </Layout>

      <Modal title="Deploy New Game Instance" open={isModalOpen} onCancel={() => setIsModalOpen(false)} onOk={() => form.submit()} okText="Deploy" className="glass-card">
        <Form form={form} layout="vertical" onFinish={handleDeploy} preserve={false}>
          <Form.Item name="game_type" label="Game Type" rules={[{ required: true }]}>
            <Select placeholder="Pick a game engine" options={[{ value: 'minecraft', label: 'Minecraft (Java Paper)' }, { value: 'nginx', label: 'Nginx (Static/Web)' }]} />
          </Form.Item>
          <Form.Item name="node_id" label="Target Node (Optional)">
            <Select 
              allowClear 
              placeholder="Automatic Selection" 
              options={nodes.filter(n => n.status === 'ONLINE').map(n => ({ 
                value: n.id, 
                label: `${n.hostname} (${n.ip}) - Load: ${Math.round((n.load_avg || 0) * 100)}%` 
              }))} 
            />
          </Form.Item>
          <Form.Item name="owner_id" label="Owner ID" rules={[{ required: true }]} initialValue="local_user">
            <Input />
          </Form.Item>
          <Form.Item name="save_path" label="S3 Archive Path (Optional)">
            <Input placeholder="s3://bucket/path/to/archive.zip" />
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  );
};

export default App;
