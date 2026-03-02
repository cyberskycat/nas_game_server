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

export const deployGame = async (gameType: string, ownerId: string, savePath?: string) => {
  const response = await api.post('/games/deploy', {
    game_type: gameType,
    owner_id: ownerId,
    save_path: savePath
  });
  return response.data;
};

export const stopGame = async (instanceId: string) => {
  const response = await api.post(`/games/${instanceId}/stop`);
  return response.data;
};

export default api;
