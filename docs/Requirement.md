### 1. 充电站结构与排队机制

#### 1.1 区域划分

如图1所示，充电站分为“充电区”和“等候区”两个区域。
电动车到达充电站后首先进入等候区，通过客户端软件向服务器提交充电请求。

服务器根据请求充电模式的不同为客户分配两种类型排队号码：

* 如果是请求“快充”模式，则号码首字母为F，后续为F类型排队顺序号(从1开始，如F1、F2)；
* 如果是请求“慢充”模式，则号码首字母为T，后续为T类型排队顺序号(从1开始，如T1、T2)。

此后，电动车在等候区等待叫号进入充电区。等候区最大车位容量为6。

#### 1.2 充电区配置

充电区安装有2个快充电桩(A、B)和3个慢充电桩(C、D、E)：

* 快充功率为30度/小时，
* 慢充功率为7度/小时。

每个充电桩设置有等长的排队队列，长度为2个车位（只有第一个车位可充电）。

---

### 2. 调度策略与叫号机制

当任意充电桩队列存在空位时，系统开始叫号：

* 按照排队顺序号“先来先到”的方式，选取等候区与该充电桩模式匹配的一辆车进入充电区（快充桩对应F类型号码，慢充桩对应T类型号码）；
* 并按照调度策略加入到匹配充电桩的排队队列中。

#### 2.1 调度策略

系统调度策略为：在对应匹配充电模式下（快充/慢充），**被调度车辆完成充电所需时长最短**。

* 等待时间 = 选定充电桩队列中所有车辆完成充电时间之和
* 自己充电时间 = 请求充电量 / 充电桩功率

**例：**
如图1所示：

* 快充桩按照 F1→F2先来先到的顺序进行叫号
* 慢充桩按照 T1→T2→T3→T4先来先到的顺序进行叫号

当F1被调度时，由于快充桩A、B均有空位，它可以分派到这两个队列；
同样当T1被调度时，它可以分派到慢充桩D、E两个队列。

最终分配需要按照调度策略，即**完成充电所需时长（等待时间 + 自己充电时间）最短**。

---

### 3. 计费规则

a) 总费用 = 充电费 + 服务费

* 充电费 = 单位电价 \* 充电度数
* 服务费 = 服务费单价 \* 充电度数

b) 单位电价（三档）：

* 峰时（1.0元/度）：10:00-15:00，18:00-21:00
* 平时（0.7元/度）：7:00-10:00，15:00-18:00，21:00-23:00
* 谷时（0.4元/度）：23:00\~次日7:00

c）服务费单价：0.8元/度
d）充电时长（小时） = 实际充电度数 / 充电功率（度/小时）

---

### 4. 系统组成与功能需求

#### 4.1 服务器端功能

* 用户信息维护
* 车辆排队号码生成
* 调度策略生成
* 计费
* 充电桩监控
* 数据统计（详单、报表数据生成）

#### 4.2 用户客户端功能

* 注册、登录
* 提交或修改充电请求（模式、充电量）
* 查看排队号码
* 查看本充电模式下前车等待数量
* 查看详单（详单编号、生成时间、桩编号、电量、时长、起止时间、费用）
* 结束充电
* 取消充电

#### 4.3 管理员客户端功能

* 启动/关闭充电桩
* 查看充电桩状态（是否正常工作、累计次数、总时长、电量）
* 查看排队车辆信息（用户ID、电池容量、请求电量、排队时长）
* 报表展示（按日/周/月：充电次数、时长、电量、费用）

---

### 5. 用户修改充电请求场景

#### 5.1 修改充电模式（快/慢充）

* 等候区允许修改，重新生成排队号，排至修改后队列末尾
* 充电区不允许修改，可取消充电并重新排队

#### 5.2 修改请求充电量

* 等候区允许修改，排队号不变
* 充电区不允许修改，可取消充电后重新排队

#### 5.3 取消充电

* 等候区、充电区均允许

---

### 6. 充电桩故障处理

若充电桩发生故障（仅考虑单一桩故障，且该桩有车排队）：

* 正在充电的车辆停止计费，本次详单结束
* 系统重新为故障桩队列中的车辆调度

#### 6.1 调度方式

a) **优先级调度**

* 暂停等候区叫号
* 先调度故障队列中车辆，之后恢复正常叫号

b) **时间顺序调度**

* 故障车辆与其它同类未充电车辆合并排序调度
* 调度完毕后恢复叫号服务

c) **故障桩恢复后的处理**

* 若其它同类桩仍有排队车辆，则统一重新调度后恢复叫号服务

---

### 7. 扩展调度请求（选做）

#### 7.1 单次调度总充电时长最短

* 当充电桩出现M个空位，可一次性叫N个号(N≤M)
* 所叫车辆不按编号顺序调度，而是统一调度，目标为**最短总完成时长**

**例：**
快充桩A、B空，F1、F2进入；
慢充桩D、E空，T1、T2、T3进入；
统一调度分配方案由策略决定。

#### 7.2 批量调度总充电时长最短

* 当到达车辆数 ≥ 充电区车位总数（如10个）时进行一次性调度
* 所有车辆统一调度，不考虑充电模式
* 分配目标为总等待+充电时长最小

**例：**
10车到达后同时叫号进入，不按编号顺序或模式分类，而统一优化分配。

#### 7.3 特殊说明

以上两种扩展调度均不考虑修改请求与充电桩故障情况。

---

### 8. 参数设置（用于验收测试）

* 快充电桩数量：`FastChargingPileNum`
* 慢充电桩数量：`TrickleChargingPileNum`
* 等候区容量：`WaitingAreaSize`
* 每桩排队队列长度：`ChargingQueueLen`
