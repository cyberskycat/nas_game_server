import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

export const getNodes = async () => {
  const response = await api.get('/nodes');
  return response.data;
};

export const getInstances = async () => {
  const response = await api.get('/instances');
  return response.data;
};

export const deployGame = async (
  gameType: string, 
  ownerId: string, 
  nodeId?: string, 
  archive?: File,
  onProgress?: (progressEvent: any) => void
) => {
  const formData = new FormData();
  formData.append('game_type', gameType);
  formData.append('owner_id', ownerId);
  if (nodeId) formData.append('node_id', nodeId);
  if (archive) formData.append('archive', archive);

  const response = await api.post('/games/deploy', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress
  });
  return response.data;
};

export const stopGame = async (instanceId: string) => {
  const response = await api.post(`/games/${instanceId}/stop`);
  return response.data;
};

export const getUploadedFiles = async () => {
  const response = await api.get('/uploaded_files');
  return response.data;
};

export default api;
