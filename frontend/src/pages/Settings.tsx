// frontend/src/pages/Settings.tsx
// Urban Intelligence Framework - Settings Page

import { useState } from "react";
import {
  Settings as SettingsIcon,
  Bell,
  Database,
  Cpu,
  RefreshCw,
  Save,
  CheckCircle,
  Trash2,
} from "lucide-react";
import {
  Card,
  CardHeader,
  CardContent,
  CardTitle,
  Button,
  Input,
  Select,
  Badge,
} from "@/components/ui";
import { useHealth, useLocalStorage } from "@/hooks";
import { cn } from "@/utils";

export function Settings() {
  const { data: health } = useHealth();
  const [notifications, setNotifications] = useLocalStorage(
    "notifications",
    true,
  );
  const [autoRetrain, setAutoRetrain] = useLocalStorage("autoRetrain", false);
  const [driftThreshold, setDriftThreshold] = useLocalStorage(
    "driftThreshold",
    "medium",
  );

  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    // Simulate save
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setIsSaving(false);
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Settings
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Configure your Urban Intelligence platform
        </p>
      </div>

      {/* System Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-primary-600" />
            System Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <StatusRow
              label="API Server"
              status={health?.status || "unknown"}
              description="FastAPI backend service"
            />
            <StatusRow
              label="ML Model"
              status={health?.model_loaded ? "healthy" : "unhealthy"}
              description={health?.version || "Not loaded"}
            />
            <StatusRow
              label="Database"
              status={health?.database_connected ? "healthy" : "unhealthy"}
              description="DuckDB analytics engine"
            />
            <StatusRow
              label="Cache"
              status="healthy"
              description="In-memory data cache"
            />
          </div>
        </CardContent>
      </Card>

      {/* Notifications */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-primary-600" />
            Notifications
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <ToggleSetting
            label="Enable Notifications"
            description="Receive alerts for drift detection and performance issues"
            enabled={notifications}
            onChange={setNotifications}
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Select
              label="Alert Severity"
              options={[
                { value: "all", label: "All alerts" },
                { value: "warning", label: "Warning and above" },
                { value: "error", label: "Errors only" },
              ]}
            />
            <Input
              label="Email for alerts"
              placeholder="your@email.com"
              type="email"
            />
          </div>
        </CardContent>
      </Card>

      {/* Model Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <RefreshCw className="w-5 h-5 text-primary-600" />
            Model Retraining
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <ToggleSetting
            label="Automatic Retraining"
            description="Automatically retrain model when drift is detected"
            enabled={autoRetrain}
            onChange={setAutoRetrain}
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Select
              label="Drift Threshold"
              options={[
                { value: "low", label: "Low (sensitive)" },
                { value: "medium", label: "Medium (balanced)" },
                { value: "high", label: "High (conservative)" },
              ]}
              value={driftThreshold}
              onChange={(e) => setDriftThreshold(e.target.value)}
            />
            <Select
              label="Retraining Schedule"
              options={[
                { value: "daily", label: "Daily" },
                { value: "weekly", label: "Weekly" },
                { value: "monthly", label: "Monthly" },
                { value: "manual", label: "Manual only" },
              ]}
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Minimum samples for retraining"
              type="number"
              defaultValue="1000"
            />
            <Input label="Optuna trials" type="number" defaultValue="50" />
          </div>
        </CardContent>
      </Card>

      {/* Data Management */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="w-5 h-5 text-primary-600" />
            Data Management
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Select
              label="Data Retention"
              options={[
                { value: "30", label: "30 days" },
                { value: "90", label: "90 days" },
                { value: "180", label: "180 days" },
                { value: "365", label: "1 year" },
              ]}
            />
            <Select
              label="Cache TTL"
              options={[
                { value: "1", label: "1 hour" },
                { value: "6", label: "6 hours" },
                { value: "24", label: "24 hours" },
                { value: "168", label: "1 week" },
              ]}
            />
          </div>
          <div className="flex gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button variant="outline" size="sm">
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh Cache
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="text-red-600 hover:bg-red-50"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Clear All Data
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* API Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <SettingsIcon className="w-5 h-5 text-primary-600" />
            API Configuration
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input label="API Host" defaultValue="localhost" />
            <Input label="API Port" type="number" defaultValue="8000" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Rate Limit (requests/min)"
              type="number"
              defaultValue="100"
            />
            <Input
              label="Request Timeout (seconds)"
              type="number"
              defaultValue="30"
            />
          </div>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex items-center justify-between py-4 border-t border-gray-200 dark:border-gray-700">
        <div>
          {saveSuccess && (
            <div className="flex items-center gap-2 text-green-600">
              <CheckCircle className="w-4 h-4" />
              <span className="text-sm">Settings saved successfully</span>
            </div>
          )}
        </div>
        <Button onClick={handleSave} loading={isSaving}>
          <Save className="w-4 h-4 mr-2" />
          Save Settings
        </Button>
      </div>
    </div>
  );
}

function StatusRow({
  label,
  status,
  description,
}: {
  label: string;
  status: string;
  description: string;
}) {
  const isHealthy = status === "healthy";

  return (
    <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
      <div className="flex items-center gap-3">
        <div
          className={cn(
            "w-2.5 h-2.5 rounded-full",
            isHealthy
              ? "bg-green-500"
              : status === "unknown"
                ? "bg-gray-400"
                : "bg-red-500",
          )}
        />
        <div>
          <p className="font-medium text-gray-900 dark:text-white">{label}</p>
          <p className="text-sm text-gray-500">{description}</p>
        </div>
      </div>
      <Badge variant={isHealthy ? "success" : "error"}>{status}</Badge>
    </div>
  );
}

function ToggleSetting({
  label,
  description,
  enabled,
  onChange,
}: {
  label: string;
  description: string;
  enabled: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <p className="font-medium text-gray-900 dark:text-white">{label}</p>
        <p className="text-sm text-gray-500">{description}</p>
      </div>
      <button
        onClick={() => onChange(!enabled)}
        className={cn(
          "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
          enabled ? "bg-primary-600" : "bg-gray-300 dark:bg-gray-600",
        )}
      >
        <span
          className={cn(
            "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
            enabled ? "translate-x-6" : "translate-x-1",
          )}
        />
      </button>
    </div>
  );
}

export default Settings;
