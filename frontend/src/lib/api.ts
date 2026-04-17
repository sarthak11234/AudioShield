const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface Task {
    id: string;
    original_name: string;
    status: 'queued' | 'processing' | 'completed' | 'failed' | 'expired';
    created_at: string;
    processed_at?: string;
    error_message?: string;
}

export interface TaskStatus {
    id: string;
    status: string;
    progress?: string;
}

export interface UserData {
    id: string;
    email: string;
    username: string;
    created_at: string;
}

export interface TokenResponse {
    access_token: string;
    token_type: string;
    user: UserData;
}

class ApiClient {
    private baseUrl: string;
    private token: string | null = null;

    constructor(baseUrl: string = API_BASE) {
        this.baseUrl = baseUrl;
    }

    setToken(token: string | null) {
        this.token = token;
    }

    private authHeaders(): Record<string, string> {
        if (!this.token) return {};
        return { Authorization: `Bearer ${this.token}` };
    }

    // ─── Auth ────────────────────────────────────────

    async signup(username: string, email: string, password: string): Promise<TokenResponse> {
        const res = await fetch(`${this.baseUrl}/api/auth/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Signup failed');
        }
        return res.json();
    }

    async login(email: string, password: string): Promise<TokenResponse> {
        const res = await fetch(`${this.baseUrl}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Invalid credentials');
        }
        return res.json();
    }

    async getMe(): Promise<UserData> {
        const res = await fetch(`${this.baseUrl}/api/auth/me`, {
            headers: this.authHeaders(),
        });
        if (!res.ok) throw new Error('Not authenticated');
        return res.json();
    }

    // ─── Health ──────────────────────────────────────

    async health(): Promise<{ status: string; service: string }> {
        const res = await fetch(`${this.baseUrl}/health`);
        if (!res.ok) throw new Error('API not available');
        return res.json();
    }

    // ─── Files ───────────────────────────────────────

    async uploadFile(
        file: File,
        onProgress?: (progress: number) => void
    ): Promise<Task> {
        const formData = new FormData();
        formData.append('file', file);

        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable && onProgress) {
                    onProgress(Math.round((e.loaded / e.total) * 100));
                }
            });

            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve(JSON.parse(xhr.responseText));
                } else {
                    reject(new Error(xhr.responseText || 'Upload failed'));
                }
            });

            xhr.addEventListener('error', () => reject(new Error('Network error')));

            xhr.open('POST', `${this.baseUrl}/api/upload`);
            if (this.token) {
                xhr.setRequestHeader('Authorization', `Bearer ${this.token}`);
            }
            xhr.send(formData);
        });
    }

    async getTaskStatus(taskId: string): Promise<TaskStatus> {
        const res = await fetch(`${this.baseUrl}/api/status/${taskId}`, {
            headers: this.authHeaders(),
        });
        if (!res.ok) throw new Error('Failed to get task status');
        return res.json();
    }

    async getTask(taskId: string): Promise<Task> {
        const res = await fetch(`${this.baseUrl}/api/task/${taskId}`, {
            headers: this.authHeaders(),
        });
        if (!res.ok) throw new Error('Task not found');
        return res.json();
    }

    async getTasks(): Promise<Task[]> {
        const res = await fetch(`${this.baseUrl}/api/tasks`, {
            headers: this.authHeaders(),
        });
        if (!res.ok) throw new Error('Failed to fetch tasks');
        return res.json();
    }

    async deleteTask(taskId: string): Promise<void> {
        const res = await fetch(`${this.baseUrl}/api/task/${taskId}`, {
            method: 'DELETE',
            headers: this.authHeaders(),
        });
        if (!res.ok) throw new Error('Failed to delete task');
    }

    getDownloadUrl(taskId: string): string {
        return `${this.baseUrl}/api/download/${taskId}`;
    }

    // ─── Polling ─────────────────────────────────────

    async pollTaskStatus(
        taskId: string,
        onUpdate: (status: TaskStatus) => void,
        intervalMs: number = 2000
    ): Promise<Task> {
        return new Promise((resolve, reject) => {
            const poll = async () => {
                try {
                    const status = await this.getTaskStatus(taskId);
                    onUpdate(status);

                    if (status.status === 'completed') {
                        const task = await this.getTask(taskId);
                        resolve(task);
                    } else if (status.status === 'failed') {
                        reject(new Error('Processing failed'));
                    } else {
                        setTimeout(poll, intervalMs);
                    }
                } catch (error) {
                    reject(error);
                }
            };
            poll();
        });
    }
}

export const api = new ApiClient();
