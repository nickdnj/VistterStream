import React from 'react';
import { render, screen } from '@testing-library/react';
import Dashboard from './components/Dashboard';
import { cameraService } from './services/cameraService';
import { api } from './services/api';

jest.mock(
  'react-router-dom',
  () => ({
    Link: ({ children, to, ...props }: any) => (
      <a href={typeof to === 'string' ? to : '#'} {...props}>
        {children}
      </a>
    ),
  }),
  { virtual: true }
);

jest.mock('./services/cameraService', () => ({
  cameraService: {
    getCameras: jest.fn(),
  },
}));

jest.mock('./services/api', () => ({
  api: {
    get: jest.fn(),
  },
}));

describe('Dashboard', () => {
  const mockGetCameras = cameraService.getCameras as jest.MockedFunction<typeof cameraService.getCameras>;
  const mockApiGet = api.get as jest.MockedFunction<typeof api.get>;

  beforeEach(() => {
    mockGetCameras.mockResolvedValue([]);
    mockApiGet.mockResolvedValue({
      data: {
        status: 'online',
        uptime: 3600,
        cpu_usage: 25,
        memory_usage: 55,
        disk_usage: 40,
        active_cameras: 0,
        active_streams: 0,
      },
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders the dashboard heading after loading completes', async () => {
    render(<Dashboard />);

    expect(await screen.findByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
  });
});
