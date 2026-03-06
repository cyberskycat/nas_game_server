import React, { useState, useEffect } from 'react';
import { Layout, Menu, Typography, Space, Card, Row, Col, Statistic, Table, Tag, Button, Progress, message, Modal, Form, Input, Select, Upload } from 'antd';
import { 
  BarChart3, 
  Server, 
  Gamepad2, 
  Activity, 
  Settings, 
  Terminal,
  Plus,
  UploadCloud,
  History,
  FileArchive
} from 'lucide-react';
import { motion } from 'framer-motion';
import { getNodes, getInstances, deployGame, stopGame, getUploadedFiles } from './services/api';

const { Content, Sider } = Layout;
const { Title, Text } = Typography;

const App: React.FC = () => {
  const [nodes, setNodes] = useState<any[]>([]);
  const [instances, setInstances] = useState<any[]>([]);
  const [uploadedFiles, setUploadedFiles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedKey, setSelectedKey] = useState('1');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [isUploading, setIsUploading] = useState<boolean>(false);
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
      const [nodesData, instancesData, uploadsData] = await Promise.all([
        getNodes(),
        getInstances(),
        getUploadedFiles()
      ]);
      setNodes(Object.values(nodesData));
      setInstances(Object.values(instancesData));
      setUploadedFiles(uploadsData);
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
      const archiveFile = values.archive?.fileList ? values.archive.fileList[0]?.originFileObj : (values.archive?.[0]?.originFileObj || null);
      if (archiveFile) {
        setIsUploading(true);
        setUploadProgress(0);
      }
      await deployGame(values.game_type, values.owner_id, values.node_id, archiveFile, (event: any) => {
        if (event.total) {
          const percent = Math.round((event.loaded * 100) / event.total);
          setUploadProgress(percent);
        }
      });
      message.success('Deployment queued');
      setIsModalOpen(false);
      form.resetFields();
      fetchData();
    } catch (error) {
      message.error('Failed to deploy game');
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
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
    { title: 'Node ID & Host', dataIndex: 'id', key: 'id', render: (id: string, record: any) => (
      <div>
        <Text strong style={{ fontSize: '13px', display: 'block' }}>{id}</Text>
        <Text type="secondary" style={{ fontSize: '12px' }}>Host: {record.hostname}</Text>
      </div>
    )},
    { title: 'IP', dataIndex: 'ip', key: 'ip' },
    { title: 'CPU Load', dataIndex: 'load_avg', key: 'load_avg', render: (val: number) => <Progress percent={Math.round((val || 0) * 100)} size="small" strokeColor="#1890ff" /> },
    { title: 'Instances / Max', dataIndex: 'running_instances', key: 'running_instances', render: (val: number, record: any) => {
      const max = record.resources?.max_game_instances || 3;
      return `${val} / ${max}`;
    }},
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
    { title: 'Node', dataIndex: 'node_id', key: 'node_id', ellipsis: true, render: (nodeId: string) => {
      const node = nodes.find(n => n.id === nodeId);
      return node ? (
        <div>
          <Text style={{ fontSize: '13px', display: 'block' }}>{nodeId}</Text>
          <Text type="secondary" style={{ fontSize: '12px' }}>{node.hostname} ({node.ip})</Text>
        </div>
      ) : nodeId;
    }},
    { title: 'Status', dataIndex: 'status', key: 'status', render: (status: string) => <Tag color={status === 'RUNNING' ? 'green' : 'orange'}>{status}</Tag> },
    { title: 'Connection Details', dataIndex: 'details', key: 'details', render: (text: string) => text ? <Text copyable type="secondary" style={{ fontSize: '12px' }}>{text}</Text> : '-' },
    { title: 'Actions', key: 'actions', render: (_: any, record: any) => (
      <Button type="link" danger size="small" onClick={() => handleStop(record.id)}>Stop</Button>
    )},
  ];

  const uploadColumns = [
    { title: 'Filename', dataIndex: 'filename', key: 'filename', render: (text: string) => <Space><FileArchive size={14} />{text}</Space> },
    { title: 'Game', dataIndex: 'game_type', key: 'game_type', render: (val: string) => <Tag color="blue">{val?.toUpperCase()}</Tag> },
    { title: 'Size', dataIndex: 'file_size', key: 'file_size', render: (val: number) => (val / 1024 / 1024).toFixed(2) + ' MB' },
    { title: 'Target Node', dataIndex: 'node_id', key: 'node_id', ellipsis: true },
    { title: 'Instance ID', dataIndex: 'instance_id', key: 'instance_id', ellipsis: true },
    { title: 'Created', dataIndex: 'created_at', key: 'created_at', render: (ts: string) => new Date(ts).toLocaleString() },
    { 
      title: 'Status', 
      dataIndex: 'is_deleted', 
      key: 'is_deleted', 
      render: (deleted: number) => (
        <Tag color={deleted ? 'default' : 'success'}>
          {deleted ? 'Deleted from S3' : 'Active in S3'}
        </Tag>
      ) 
    },
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
          selectedKeys={[selectedKey]}
          onClick={({ key }) => setSelectedKey(key)}
          style={{ background: 'transparent', border: 'none' }}
          items={[
            { key: '1', icon: <BarChart3 size={18} />, label: 'Dashboard' },
            { key: '6', icon: <History size={18} />, label: 'Upload History' },
            { key: '2', icon: <Server size={18} />, label: 'Infrastructure' },
            { key: '3', icon: <Gamepad2 size={18} />, label: 'Active Games' },
            { key: '4', icon: <Terminal size={18} />, label: 'System Logs' },
            { key: '5', icon: <Settings size={18} />, label: 'Global Settings' },
          ]}
        />
      </Sider>
      
      <Layout style={{ background: 'transparent' }}>
        <Content style={{ padding: '24px', overflowY: 'auto' }}>
          {selectedKey === '1' && (
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
          )}

          {selectedKey === '6' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <div style={{ marginBottom: '24px' }}>
                <Title level={2} style={{ margin: 0 }}>Upload History</Title>
                <Text type="secondary">Track and manage service archives uploaded via Center</Text>
              </div>

              <Card className="glass-card" title={<Space><History size={18} /> Uploaded Files Records (S3 Retention policy applied)</Space>}>
                <Table 
                  columns={uploadColumns} 
                  dataSource={uploadedFiles} 
                  rowKey="id" 
                  size="small" 
                  loading={loading}
                  pagination={{ pageSize: 10 }}
                />
              </Card>
            </motion.div>
          )}

          {['2', '3', '4', '5'].includes(selectedKey) && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
               <Card className="glass-card" style={{ textAlign: 'center', padding: '100px 0' }}>
                 <Statistic title="Module Under Construction" value={selectedKey} prefix="Feature ID #" />
                 <Text type="secondary">This section is coming soon as part of the phase 2 roadmap.</Text>
               </Card>
            </motion.div>
          )}
        </Content>
      </Layout>

      <Modal 
        title="Deploy New Game Instance" 
        open={isModalOpen} 
        onCancel={() => !isUploading && setIsModalOpen(false)} 
        onOk={() => form.submit()} 
        okText={isUploading ? "Uploading..." : "Deploy"} 
        confirmLoading={isUploading}
        okButtonProps={{ disabled: isUploading }}
        cancelButtonProps={{ disabled: isUploading }}
        closable={!isUploading}
        maskClosable={!isUploading}
        className="glass-card"
      >
        <Form form={form} layout="vertical" onFinish={handleDeploy} preserve={false}>
          <Form.Item name="game_type" label="Game Type" rules={[{ required: true }]}>
            <Select placeholder="Pick a game engine" options={[{ value: 'minecraft', label: 'Minecraft' }, { value: 'nginx', label: 'Nginx (Static/Web)' }]} />
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
          <Form.Item 
            name="archive" 
            label="Upload Local Archive (Optional)" 
            valuePropName="fileList" 
            getValueFromEvent={(e: any) => {
              if (Array.isArray(e)) return e;
              return e?.fileList;
            }}
          >
            <Upload beforeUpload={() => false} maxCount={1} accept=".zip" disabled={isUploading}>
              <Button icon={<UploadCloud size={16} />} disabled={isUploading}>Select Archive (.zip)</Button>
            </Upload>
          </Form.Item>
          {isUploading && (
            <div style={{ marginTop: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <Text type="secondary" style={{ fontSize: '13px' }}>{uploadProgress < 100 ? "Uploading to Center..." : "Building on Center..."}</Text>
                <Text type="secondary" style={{ fontSize: '13px' }}>{uploadProgress}%</Text>
              </div>
              <Progress percent={uploadProgress} showInfo={false} status={uploadProgress === 100 ? "active" : "normal"} />
            </div>
          )}
        </Form>
      </Modal>
    </Layout>
  );
};

export default App;
