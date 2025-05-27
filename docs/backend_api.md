根据您提供的代码，我来为您生成一份完整的后端API说明文档。

# 电动车充电站管理系统 - 后端API说明文档

**Base URL (Railway Private):** `http://bubbly-generosity.railway.internal`  
**Base URL (Public):** `https://elecharge-backend.up.railway.app`  
**API Version:** v1  
**Content-Type:** `application/json`
## 📋 基础信息

**Base URL:** `https://your-domain.com/api/`  
**认证方式:** Token Authentication  
**Content-Type:** `application/json`

---

## 🔐 1. 用户认证模块 (accounts)

### 1.1 用户注册
```http
POST /api/auth/register/
```

**请求体:**
```json
{
  "username": "string",
  "password": "string", 
  "email": "string",
  "phone": "string"
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
POST /api/auth/login/
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
    "is_staff": "boolean"
  }
}
```

### 1.3 用户登出
```http
POST /api/auth/logout/
```

**Headers:** `Authorization: Token <token>`

**响应:**
```json
{
  "success": true,
  "message": "登出成功"
}
```

### 1.4 获取用户信息
```http
GET /api/auth/profile/
```

**Headers:** `Authorization: Token <token>`

**响应:**
```json
{
  "success": true,
  "data": {
    "id": "integer",
    "username": "string",
    "email": "string", 
    "phone": "string",
    "is_staff": "boolean"
  }
}
```

---

## ⚡ 2. 充电管理模块 (charging)

### 2.1 充电请求管理

#### 2.1.1 提交充电请求
```http
POST /api/charging/request/
```

**Headers:** `Authorization: Token <token>`

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

#### 2.1.2 修改充电请求
```http
PUT /api/charging/request/{request_id}/
```

**Headers:** `Authorization: Token <token>`

**请求体:**
```json
{
  "charging_mode": "fast|slow",
  "requested_amount": "number"
}
```

#### 2.1.3 取消充电请求
```http
DELETE /api/charging/request/{request_id}/cancel/
```

**Headers:** `Authorization: Token <token>`

#### 2.1.4 查看当前充电请求状态
```http
GET /api/charging/request/status/
```

**Headers:** `Authorization: Token <token>`

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

#### 2.1.5 结束充电
```http
POST /api/charging/complete/
```

**Headers:** `Authorization: Token <token>`

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

### 2.2 排队信息

#### 2.2.1 查看排队状态
```http
GET /api/charging/queue/status/
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

#### 2.2.2 查看充电桩状态
```http
GET /api/charging/piles/status/
```

**响应:**
```json
{
  "success": true,
  "data": {
    "fast_piles": [
      {
        "pile_id": "string",
        "pile_type": "fast",
        "status": "normal|fault|offline",
        "is_working": "boolean",
        "current_user": "string|null",
        "queue": []
      }
    ],
    "slow_piles": [
      {
        "pile_id": "string",
        "pile_type": "slow", 
        "status": "normal|fault|offline",
        "is_working": "boolean",
        "current_user": "string|null",
        "queue": []
      }
    ]
  }
}
```

### 2.3 账单管理

#### 2.3.1 查看充电详单列表
```http
GET /api/charging/bills/
```

**Headers:** `Authorization: Token <token>`

**查询参数:**
- `page`: integer (页码，默认1)
- `limit`: integer (每页数量，默认20)
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
        "peak_cost": "number",
        "normal_cost": "number",
        "valley_cost": "number",
        "service_cost": "number",
        "total_cost": "number"
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

#### 2.3.2 查看单个详单
```http
GET /api/charging/bills/{bill_id}/
```

**Headers:** `Authorization: Token <token>`

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

### 2.4 通知管理

#### 2.4.1 获取用户通知
```http
GET /api/charging/notifications/
```

**Headers:** `Authorization: Token <token>`

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

#### 2.4.2 标记通知已读
```http
PUT /api/charging/notifications/{notification_id}/read/
```

**Headers:** `Authorization: Token <token>`

### 2.5 系统配置

#### 2.5.1 获取系统参数
```http
GET /api/charging/config/parameters/
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

---

## 🔧 3. 数据模型

### 3.1 用户模型 (User)
- `id`: 用户ID
- `username`: 用户名
- `email`: 邮箱
- `phone`: 手机号
- `is_staff`: 是否为管理员

### 3.2 充电桩模型 (ChargingPile)
- `pile_id`: 充电桩ID (主键)
- `pile_type`: 充电桩类型 (fast/slow)
- `status`: 状态 (normal/fault/offline)
- `is_working`: 是否正在工作
- `total_sessions`: 总充电次数
- `total_revenue`: 总收入

### 3.3 充电请求模型 (ChargingRequest)
- `id`: 请求ID (UUID)
- `user`: 用户
- `queue_number`: 队列号
- `charging_mode`: 充电模式 (fast/slow)
- `requested_amount`: 请求充电量
- `current_status`: 当前状态 (waiting/charging/completed/cancelled)
- `queue_position`: 排队位置

### 3.4 充电会话模型 (ChargingSession)
- `id`: 会话ID (UUID)
- `request`: 关联的充电请求
- `pile`: 充电桩
- `user`: 用户
- `start_time`: 开始时间
- `end_time`: 结束时间
- `charging_amount`: 实际充电量
- `total_cost`: 总费用

### 3.5 系统参数模型 (SystemParameter)
- `param_key`: 参数键
- `param_value`: 参数值
- `param_type`: 参数类型 (int/float/string/boolean/json)
- `description`: 参数描述
- `is_editable`: 是否可编辑

### 3.6 通知模型 (Notification)
- `user`: 用户
- `type`: 通知类型
- `message`: 通知消息
- `read`: 是否已读
- `created_at`: 创建时间

---

## 📊 4. 业务逻辑

### 4.1 充电流程
1. **提交请求** → 用户提交充电请求
2. **排队等待** → 系统分配排队位置
3. **自动分配** → 有空闲充电桩时自动开始充电
4. **充电中** → 实时监控充电状态
5. **完成充电** → 生成账单，释放充电桩

### 4.2 计费规则
- **峰时电价** (10:00-15:00, 18:00-21:00): 1.2元/kWh
- **平时电价** (07:00-10:00, 15:00-18:00, 21:00-23:00): 0.8元/kWh
- **谷时电价** (23:00-07:00): 0.4元/kWh
- **服务费**: 0.8元/kWh

### 4.3 排队机制
- 按充电模式分别排队 (快充/慢充)
- 先到先服务 (FIFO)
- 等候区容量限制
- 自动分配空闲充电桩

---

## ⚠️ 5. 错误响应格式

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
- `DUPLICATE_REQUEST`: 重复请求
- `SYSTEM_ERROR`: 系统错误

---

## 🎯 6. 已实现功能总结

### ✅ 用户管理
- 用户注册/登录/登出
- 用户信息管理
- Token认证

### ✅ 充电管理
- 充电请求提交/修改/取消
- 实时排队状态查询
- 充电桩状态监控
- 自动充电桩分配

### ✅ 账单系统
- 分时段计费
- 充电详单生成
- 费用明细查询

### ✅ 通知系统
- 实时状态通知
- 消息推送管理

### ✅ 系统配置
- 动态参数配置
- 充电桩数量管理
- 费率设置

### ✅ 管理后台
- Django Admin集成
- 系统参数管理
- 数据统计查看

这个系统已经实现了电动车充电站管理的核心功能，包括完整的用户管理、充电流程、计费系统和管理功能！🚀
