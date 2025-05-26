
```
Private URL -- 开发过程可以使用此url
- backend: bubbly-generosity.railway.internal
```


根据您的需求文档，我来为您生成完整的REST API文档。这个API文档将涵盖电动车充电站管理系统的所有功能需求。

# 电动车充电站管理系统 REST API 文档

## 基础信息

**Base URL (Railway Private):** `http://bubbly-generosity.railway.internal`  
**Base URL (Public):** `https://elecharge-backend.up.railway.app`  
**API Version:** v1  
**Content-Type:** `application/json`

---

## 1. 认证相关 API

### 1.1 用户注册
```http
POST /api/auth/register
```

**请求体:**
```json
{
  "username": "string",
  "password": "string",
  "email": "string",
  "phone": "string",
  "vehicle_info": {
    "license_plate": "string",
    "battery_capacity": "number"
  }
}
```

**响应:**
```json
{
  "success": true,
  "message": "注册成功",
  "data": {
    "user_id": "integer",
    "username": "string",
    "token": "string"
  }
}
```

### 1.2 用户登录
```http
POST /api/auth/login
```

**请求体:**
```json
{
  "username": "string",
  "password": "string"
}
```

**响应:**
```json
{
  "success": true,
  "message": "登录成功",
  "data": {
    "user_id": "integer",
    "username": "string",
    "token": "string",
    "is_admin": "boolean"
  }
}
```

### 1.3 用户登出
```http
POST /api/auth/logout
```

**Headers:** `Authorization: Bearer <token>`

---

## 2. 充电请求管理 API

### 2.1 提交充电请求
```http
POST /api/charging/request
```

**Headers:** `Authorization: Bearer <token>`

**请求体:**
```json
{
  "charging_mode": "fast|slow",
  "requested_amount": "number",
  "battery_capacity": "number"
}
```

**响应:**
```json
{
  "success": true,
  "message": "充电请求提交成功",
  "data": {
    "queue_number": "string",
    "charging_mode": "string",
    "requested_amount": "number",
    "estimated_wait_time": "number",
    "queue_position": "integer"
  }
}
```

### 2.2 修改充电请求
```http
PUT /api/charging/request/{request_id}
```

**Headers:** `Authorization: Bearer <token>`

**请求体:**
```json
{
  "charging_mode": "fast|slow",
  "requested_amount": "number"
}
```

**响应:**
```json
{
  "success": true,
  "message": "充电请求修改成功",
  "data": {
    "queue_number": "string",
    "new_position": "integer",
    "estimated_wait_time": "number"
  }
}
```

### 2.3 取消充电请求
```http
DELETE /api/charging/request/{request_id}
```

**Headers:** `Authorization: Bearer <token>`

**响应:**
```json
{
  "success": true,
  "message": "充电请求已取消"
}
```

### 2.4 查看当前充电请求状态
```http
GET /api/charging/request/status
```

**Headers:** `Authorization: Bearer <token>`

**响应:**
```json
{
  "success": true,
  "data": {
    "queue_number": "string",
    "charging_mode": "string",
    "requested_amount": "number",
    "current_status": "waiting|charging|completed",
    "queue_position": "integer",
    "ahead_count": "integer",
    "estimated_wait_time": "number",
    "charging_pile_id": "string|null",
    "start_time": "datetime|null",
    "current_amount": "number"
  }
}
```

### 2.5 结束充电
```http
POST /api/charging/complete
```

**Headers:** `Authorization: Bearer <token>`

**响应:**
```json
{
  "success": true,
  "message": "充电已结束",
  "data": {
    "bill_id": "string",
    "total_amount": "number",
    "total_cost": "number",
    "charging_duration": "number"
  }
}
```

---

## 3. 排队信息 API

### 3.1 查看排队状态
```http
GET /api/queue/status
```

**响应:**
```json
{
  "success": true,
  "data": {
    "fast_charging": {
      "waiting_count": "integer",
      "queue_list": [
        {
          "queue_number": "string",
          "estimated_wait_time": "number"
        }
      ]
    },
    "slow_charging": {
      "waiting_count": "integer", 
      "queue_list": [
        {
          "queue_number": "string",
          "estimated_wait_time": "number"
        }
      ]
    },
    "waiting_area_capacity": {
      "current": "integer",
      "max": "integer"
    }
  }
}
```

### 3.2 查看充电桩状态
```http
GET /api/piles/status
```

**响应:**
```json
{
  "success": true,
  "data": {
    "fast_piles": [
      {
        "pile_id": "string",
        "status": "available|occupied|fault",
        "current_user": "string|null",
        "queue": [
          {
            "queue_number": "string",
            "estimated_completion": "datetime"
          }
        ]
      }
    ],
    "slow_piles": [
      {
        "pile_id": "string", 
        "status": "available|occupied|fault",
        "current_user": "string|null",
        "queue": [
          {
            "queue_number": "string",
            "estimated_completion": "datetime"
          }
        ]
      }
    ]
  }
}
```

---

## 4. 账单管理 API

### 4.1 查看充电详单
```http
GET /api/bills
```

**Headers:** `Authorization: Bearer <token>`

**查询参数:**
- `page`: integer (页码，默认1)
- `limit`: integer (每页数量，默认10)
- `start_date`: date (开始日期)
- `end_date`: date (结束日期)

**响应:**
```json
{
  "success": true,
  "data": {
    "bills": [
      {
        "bill_id": "string",
        "generated_time": "datetime",
        "pile_id": "string",
        "charging_amount": "number",
        "charging_duration": "number",
        "start_time": "datetime",
        "end_time": "datetime",
        "charging_cost": "number",
        "service_cost": "number",
        "total_cost": "number",
        "peak_hours": "number",
        "normal_hours": "number",
        "valley_hours": "number"
      }
    ],
    "pagination": {
      "current_page": "integer",
      "total_pages": "integer",
      "total_count": "integer"
    }
  }
}
```

### 4.2 查看单个详单
```http
GET /api/bills/{bill_id}
```

**Headers:** `Authorization: Bearer <token>`

**响应:**
```json
{
  "success": true,
  "data": {
    "bill_id": "string",
    "generated_time": "datetime",
    "pile_id": "string",
    "charging_amount": "number",
    "charging_duration": "number",
    "start_time": "datetime",
    "end_time": "datetime",
    "cost_breakdown": {
      "peak_cost": "number",
      "normal_cost": "number", 
      "valley_cost": "number",
      "service_cost": "number",
      "total_cost": "number"
    },
    "time_breakdown": {
      "peak_hours": "number",
      "normal_hours": "number",
      "valley_hours": "number"
    }
  }
}
```

---

## 5. 管理员 API

### 5.1 充电桩管理

#### 5.1.1 启动/关闭充电桩
```http
POST /api/admin/piles/{pile_id}/toggle
```

**Headers:** `Authorization: Bearer <admin_token>`

**请求体:**
```json
{
  "action": "start|stop"
}
```

**响应:**
```json
{
  "success": true,
  "message": "充电桩状态已更新",
  "data": {
    "pile_id": "string",
    "new_status": "string"
  }
}
```

#### 5.1.2 查看充电桩详细状态
```http
GET /api/admin/piles
```

**Headers:** `Authorization: Bearer <admin_token>`

**响应:**
```json
{
  "success": true,
  "data": [
    {
      "pile_id": "string",
      "type": "fast|slow",
      "status": "normal|fault|offline",
      "is_working": "boolean",
      "statistics": {
        "total_sessions": "integer",
        "total_duration": "number",
        "total_energy": "number",
        "total_revenue": "number"
      },
      "current_session": {
        "user_id": "string|null",
        "start_time": "datetime|null",
        "current_amount": "number"
      }
    }
  ]
}
```

### 5.2 排队车辆管理

#### 5.2.1 查看排队车辆信息
```http
GET /api/admin/queue/vehicles
```

**Headers:** `Authorization: Bearer <admin_token>`

**响应:**
```json
{
  "success": true,
  "data": {
    "waiting_area": [
      {
        "user_id": "string",
        "username": "string",
        "queue_number": "string",
        "battery_capacity": "number",
        "requested_amount": "number",
        "waiting_duration": "number",
        "charging_mode": "string"
      }
    ],
    "charging_area": [
      {
        "pile_id": "string",
        "user_id": "string",
        "username": "string",
        "start_time": "datetime",
        "current_amount": "number",
        "target_amount": "number",
        "estimated_completion": "datetime"
      }
    ]
  }
}
```

### 5.3 报表统计

#### 5.3.1 获取统计报表
```http
GET /api/admin/reports
```

**Headers:** `Authorization: Bearer <admin_token>`

**查询参数:**
- `period`: string (day|week|month)
- `start_date`: date
- `end_date`: date

**响应:**
```json
{
  "success": true,
  "data": {
    "period": "string",
    "summary": {
      "total_sessions": "integer",
      "total_duration": "number",
      "total_energy": "number",
      "total_revenue": "number"
    },
    "daily_breakdown": [
      {
        "date": "date",
        "sessions": "integer",
        "duration": "number",
        "energy": "number",
        "revenue": "number"
      }
    ],
    "pile_breakdown": [
      {
        "pile_id": "string",
        "sessions": "integer",
        "duration": "number",
        "energy": "number",
        "revenue": "number",
        "utilization_rate": "number"
      }
    ]
  }
}
```

---

## 6. 系统配置 API

### 6.1 获取系统参数
```http
GET /api/config/parameters
```

**响应:**
```json
{
  "success": true,
  "data": {
    "FastChargingPileNum": "integer",
    "TrickleChargingPileNum": "integer", 
    "WaitingAreaSize": "integer",
    "ChargingQueueLen": "integer",
    "pricing": {
      "peak_rate": "number",
      "normal_rate": "number",
      "valley_rate": "number",
      "service_rate": "number"
    },
    "time_periods": {
      "peak": ["10:00-15:00", "18:00-21:00"],
      "normal": ["07:00-10:00", "15:00-18:00", "21:00-23:00"],
      "valley": ["23:00-07:00"]
    }
  }
}
```

### 6.2 更新系统参数 (管理员)
```http
PUT /api/admin/config/parameters
```

**Headers:** `Authorization: Bearer <admin_token>`

**请求体:**
```json
{
  "FastChargingPileNum": "integer",
  "TrickleChargingPileNum": "integer",
  "WaitingAreaSize": "integer", 
  "ChargingQueueLen": "integer"
}
```

---

## 7. 实时通知 API

### 7.1 获取用户通知
```http
GET /api/notifications
```

**Headers:** `Authorization: Bearer <token>`

**响应:**
```json
{
  "success": true,
  "data": [
    {
      "id": "integer",
      "type": "queue_update|charging_start|charging_complete|pile_fault",
      "message": "string",
      "timestamp": "datetime",
      "read": "boolean"
    }
  ]
}
```

### 7.2 标记通知已读
```http
PUT /api/notifications/{notification_id}/read
```

**Headers:** `Authorization: Bearer <token>`

---

## 8. 故障处理 API

### 8.1 报告充电桩故障 (管理员)
```http
POST /api/admin/piles/{pile_id}/fault
```

**Headers:** `Authorization: Bearer <admin_token>`

**请求体:**
```json
{
  "fault_description": "string",
  "fault_type": "hardware|software|other"
}
```

### 8.2 修复充电桩故障 (管理员)
```http
POST /api/admin/piles/{pile_id}/repair
```

**Headers:** `Authorization: Bearer <admin_token>`

**请求体:**
```json
{
  "repair_description": "string"
}
```

---

## 错误响应格式

所有API的错误响应都遵循以下格式：

```json
{
  "success": false,
  "error": {
    "code": "string",
    "message": "string",
    "details": "object|null"
  }
}
```

### 常见错误码

- `AUTH_REQUIRED`: 需要认证
- `AUTH_INVALID`: 认证无效
- `PERMISSION_DENIED`: 权限不足
- `VALIDATION_ERROR`: 参数验证失败
- `RESOURCE_NOT_FOUND`: 资源不存在
- `QUEUE_FULL`: 等候区已满
- `INVALID_REQUEST`: 无效请求
- `SYSTEM_ERROR`: 系统错误

---

## WebSocket 实时更新 (可选)

### 连接地址
```
ws://bubbly-generosity.railway.internal/ws/updates
```

### 消息格式
```json
{
  "type": "queue_update|charging_status|pile_status",
  "data": {
    // 具体数据根据类型而定
  }
}
```

---

这个API文档涵盖了您需求中的所有功能点，包括用户管理、充电请求、排队机制、计费、管理员功能和报表统计。您可以根据实际开发进度调整具体的实现细节。
