import { useEffect, useState } from 'react'
import { Activity, Cpu, HardDrive, Wifi, WifiOff } from 'lucide-react'
import axios from 'axios'

interface Device {
    id: string
    name: string
    is_online: boolean
    last_seen: string
    cpu_usage?: number
    memory_usage?: number
    disk_usage?: number
}

const API_URL = 'http://localhost:8001'

export default function Dashboard() {
    const [devices, setDevices] = useState<Device[]>([])
    const [loading, setLoading] = useState(true)

    const fetchDevices = async () => {
        try {
            const response = await axios.get(`${API_URL}/api/devices`)
            setDevices(response.data.devices || [])
            setLoading(false)
        } catch (error) {
            console.error('Failed to fetch devices:', error)
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchDevices()
        const interval = setInterval(fetchDevices, 3000) // Refresh every 3 seconds
        return () => clearInterval(interval)
    }, [])

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-slate-400">Loading devices...</div>
            </div>
        )
    }

    return (
        <div>
            <h1 className="text-3xl font-bold mb-8">Device Dashboard</h1>

            {devices.length === 0 ? (
                <div className="bg-slate-800 rounded-lg p-8 text-center">
                    <WifiOff className="mx-auto mb-4 text-slate-400" size={48} />
                    <h3 className="text-xl font-semibold mb-2">No Devices Connected</h3>
                    <p className="text-slate-400">
                        Waiting for VistterStream devices to connect...
                    </p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {devices.map((device) => (
                        <div
                            key={device.id}
                            className="bg-slate-800 rounded-lg p-6 border border-slate-700 hover:border-slate-600 transition-colors"
                        >
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-xl font-semibold">{device.name}</h3>
                                {device.is_online ? (
                                    <Wifi className="text-green-400" size={24} />
                                ) : (
                                    <WifiOff className="text-red-400" size={24} />
                                )}
                            </div>

                            <div className="space-y-3">
                                <div className="flex items-center gap-2 text-sm">
                                    <span className={`px-2 py-1 rounded ${device.is_online ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}`}>
                                        {device.is_online ? 'Online' : 'Offline'}
                                    </span>
                                </div>

                                {device.cpu_usage !== undefined && device.cpu_usage > 0 && (
                                    <div className="flex items-center gap-2">
                                        <Cpu size={16} className="text-slate-400" />
                                        <div className="flex-1">
                                            <div className="flex justify-between text-sm mb-1">
                                                <span>CPU</span>
                                                <span>{device.cpu_usage.toFixed(1)}%</span>
                                            </div>
                                            <div className="w-full bg-slate-700 rounded-full h-2">
                                                <div
                                                    className="bg-blue-500 h-2 rounded-full transition-all"
                                                    style={{ width: `${Math.min(device.cpu_usage, 100)}%` }}
                                                />
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {device.memory_usage !== undefined && device.memory_usage > 0 && (
                                    <div className="flex items-center gap-2">
                                        <Activity size={16} className="text-slate-400" />
                                        <div className="flex-1">
                                            <div className="flex justify-between text-sm mb-1">
                                                <span>Memory</span>
                                                <span>{device.memory_usage.toFixed(1)}%</span>
                                            </div>
                                            <div className="w-full bg-slate-700 rounded-full h-2">
                                                <div
                                                    className="bg-green-500 h-2 rounded-full transition-all"
                                                    style={{ width: `${Math.min(device.memory_usage, 100)}%` }}
                                                />
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {device.disk_usage !== undefined && device.disk_usage > 0 && (
                                    <div className="flex items-center gap-2">
                                        <HardDrive size={16} className="text-slate-400" />
                                        <div className="flex-1">
                                            <div className="flex justify-between text-sm mb-1">
                                                <span>Disk</span>
                                                <span>{device.disk_usage.toFixed(1)}%</span>
                                            </div>
                                            <div className="w-full bg-slate-700 rounded-full h-2">
                                                <div
                                                    className="bg-purple-500 h-2 rounded-full transition-all"
                                                    style={{ width: `${Math.min(device.disk_usage, 100)}%` }}
                                                />
                                            </div>
                                        </div>
                                    </div>
                                )}

                                <div className="text-xs text-slate-400 mt-4">
                                    Last seen: {new Date(device.last_seen).toLocaleString()}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            <div className="mt-8 bg-blue-900/20 border border-blue-700 rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-2 text-blue-300">Getting Started</h3>
                <p className="text-slate-300 mb-2">
                    To connect your VistterStream device:
                </p>
                <ol className="list-decimal list-inside text-slate-300 space-y-1 ml-2">
                    <li>Update the <code className="bg-slate-800 px-2 py-1 rounded">cloud_api_url</code> setting on your device</li>
                    <li>Set it to: <code className="bg-slate-800 px-2 py-1 rounded">ws://localhost:8001/ws/device</code></li>
                    <li>Click "Pair with Cloud" in your device settings</li>
                </ol>
            </div>
        </div>
    )
}
