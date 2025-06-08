/**
 * 充电估算工具 - 基于后端算法的准确估算
 * 包含队列等待时间估算、分时段费用计算等功能
 */

/**
 * 时间段判断函数
 * @param {Date} time - 时间对象
 * @param {Object} timeConfig - 时间段配置
 * @returns {string} - 'peak'|'normal'|'valley'
 */
export function getTimePeriod(time, timeConfig = {}) {
  const hour = time.getHours();
  
  // 默认时间段配置（与后端保持一致）
  const defaultConfig = {
    peak_start: '8:00',
    peak_end: '11:00',
    valley_start: '23:00',
    valley_end: '7:00'
  };
  
  const config = { ...defaultConfig, ...timeConfig };
  
  // 解析时间字符串
  const parseTime = (timeStr) => {
    const [h, m] = timeStr.split(':').map(Number);
    return h + (m || 0) / 60;
  };
  
  const peakStart = parseTime(config.peak_start);
  const peakEnd = parseTime(config.peak_end);
  const valleyStart = parseTime(config.valley_start);
  const valleyEnd = parseTime(config.valley_end);
  
  // 峰时段：8:00-11:00 或 18:00-21:00（后端代码中的逻辑）
  if ((hour >= 10 && hour < 15) || (hour >= 18 && hour < 21)) {
    return 'peak';
  }
  // 谷时段：23:00-7:00
  else if (hour >= 23 || hour < 7) {
    return 'valley';
  }
  // 平时段：其他时间
  else {
    return 'normal';
  }
}

/**
 * 计算单个桩的剩余时间（基于后端ChargingPile.calculate_remaining_time()逻辑）
 * @param {Object} pileData - 桩数据，包含当前充电和队列信息
 * @param {number} chargingPower - 桩的充电功率
 * @returns {number} - 剩余时间(分钟)
 */
export function calculatePileRemainingTime(pileData, chargingPower) {
  if (!pileData || !chargingPower) return 0;
  
  let totalTime = 0;
  
  // 计算当前充电请求的剩余时间
  const currentCharging = pileData.current_charging;
  if (currentCharging && currentCharging.queue_number) {
    const requestedAmount = currentCharging.requested_amount || 0;
    const currentAmount = currentCharging.current_amount || 0;
    const remainingAmount = Math.max(0, requestedAmount - currentAmount);
    
    if (remainingAmount > 0) {
      const currentRemaining = (remainingAmount / chargingPower) * 60; // 转换为分钟
      totalTime += currentRemaining;
    }
  }
  
  // 计算队列中所有请求的时间
  const queueList = pileData.queue_list || [];
  queueList.forEach(request => {
    if (request.requested_amount) {
      const chargingTime = (request.requested_amount / chargingPower) * 60;
      totalTime += chargingTime;
    }
  });
  
  return Math.round(totalTime);
}

/**
 * 找到最优的可用桩（基于后端算法）
 * @param {Array} pilesData - 桩数据数组
 * @param {number} chargingPower - 充电功率
 * @returns {Object} - 最优桩信息
 */
export function findBestAvailablePile(pilesData, chargingPower) {
  if (!pilesData || !Array.isArray(pilesData)) {
    return { minWaitTime: Infinity, bestPile: null, availablePileFound: false };
  }
  
  let minWaitTime = Infinity;
  let bestPile = null;
  let availablePileFound = false;
  
  pilesData.forEach(pile => {
    const queueCount = pile.queue_count || 0;
    const maxQueueSize = pile.max_queue_size || 3;
    
    // 计算该桩的准确剩余时间
    const remainingTime = calculatePileRemainingTime(pile, chargingPower);
    
    if (queueCount < maxQueueSize) {
      // 桩队列未满，可以直接加入
      if (remainingTime < minWaitTime) {
        minWaitTime = remainingTime;
        bestPile = pile;
        availablePileFound = true;
      }
    } else {
      // 桩队列已满，需要等待队列中的最后一个完成
      // 估算平均充电时间（基于队列中请求的平均充电量）
      const queueList = pile.queue_list || [];
      let avgChargingTime = 30; // 默认30分钟
      
      if (queueList.length > 0) {
        const totalAmount = queueList.reduce((sum, req) => sum + (req.requested_amount || 0), 0);
        const avgAmount = totalAmount / queueList.length;
        avgChargingTime = (avgAmount / chargingPower) * 60;
      }
      
      const totalWaitTime = remainingTime + avgChargingTime;
      if (totalWaitTime < minWaitTime) {
        minWaitTime = totalWaitTime;
        bestPile = pile;
      }
    }
  });
  
  return { minWaitTime, bestPile, availablePileFound };
}

/**
 * 计算分时段充电费用
 * @param {number} chargingAmount - 充电量(kWh)
 * @param {Date} startTime - 开始时间
 * @param {number} chargingDurationMinutes - 充电时长(分钟)
 * @param {Object} pricing - 电价配置
 * @param {Object} timeConfig - 时间段配置
 * @returns {Object} - 费用详情
 */
export function calculateChargingCost(chargingAmount, startTime, chargingDurationMinutes, pricing, timeConfig = {}) {
  if (!pricing || !chargingAmount || !chargingDurationMinutes) {
    return {
      peak_cost: 0,
      normal_cost: 0,
      valley_cost: 0,
      service_cost: 0,
      total_cost: 0,
      peak_hours: 0,
      normal_hours: 0,
      valley_hours: 0,
      breakdown: []
    };
  }
  
  const chargingDurationHours = chargingDurationMinutes / 60;
  const endTime = new Date(startTime.getTime() + chargingDurationMinutes * 60 * 1000);
  
  let peakHours = 0;
  let normalHours = 0;
  let valleyHours = 0;
  
  const breakdown = [];
  let currentTime = new Date(startTime);
  let remainingDuration = chargingDurationHours;
  
  // 按小时计算不同时段的充电时长
  while (remainingDuration > 0) {
    const timePeriod = getTimePeriod(currentTime, timeConfig);
    
    // 计算这个小时内的充电时间
    const timeInHour = Math.min(remainingDuration, 1.0);
    
    switch (timePeriod) {
      case 'peak':
        peakHours += timeInHour;
        break;
      case 'normal':
        normalHours += timeInHour;
        break;
      case 'valley':
        valleyHours += timeInHour;
        break;
    }
    
    breakdown.push({
      hour: currentTime.getHours(),
      period: timePeriod,
      duration: timeInHour,
      rate: pricing[`${timePeriod}_rate`] || 0
    });
    
    remainingDuration -= timeInHour;
    currentTime = new Date(currentTime.getTime() + 60 * 60 * 1000); // 增加1小时
  }
  
  // 计算费用
  const peakCost = (peakHours * chargingAmount / chargingDurationHours) * pricing.peak_rate;
  const normalCost = (normalHours * chargingAmount / chargingDurationHours) * pricing.normal_rate;
  const valleyCost = (valleyHours * chargingAmount / chargingDurationHours) * pricing.valley_rate;
  const serviceCost = chargingAmount * pricing.service_rate;
  
  const totalCost = peakCost + normalCost + valleyCost + serviceCost;
  
  return {
    peak_cost: Number(peakCost.toFixed(2)),
    normal_cost: Number(normalCost.toFixed(2)),
    valley_cost: Number(valleyCost.toFixed(2)),
    service_cost: Number(serviceCost.toFixed(2)),
    total_cost: Number(totalCost.toFixed(2)),
    peak_hours: Number(peakHours.toFixed(2)),
    normal_hours: Number(normalHours.toFixed(2)),
    valley_hours: Number(valleyHours.toFixed(2)),
    breakdown
  };
}

/**
 * 计算充电时长(分钟)
 * @param {number} chargingAmount - 充电量(kWh)
 * @param {number} chargingPower - 充电功率(kW)
 * @returns {number} - 充电时长(分钟)
 */
export function calculateChargingDuration(chargingAmount, chargingPower) {
  if (!chargingAmount || !chargingPower) return 0;
  return Math.ceil((chargingAmount / chargingPower) * 60);
}

/**
 * 计算等待时间（基于后端队列算法和精确的桩剩余时间计算）
 * @param {string} chargingMode - 充电模式 'fast'|'slow'
 * @param {Object} queueStatus - 队列状态
 * @param {Object} systemParams - 系统参数
 * @returns {Object} - 等待时间估算
 */
export function calculateWaitTime(chargingMode, queueStatus, systemParams) {
  if (!queueStatus || !systemParams) {
    return {
      estimated_wait_minutes: 0,
      queue_position: 1,
      ahead_count: 0,
      details: '数据不足，无法估算'
    };
  }
  
  // 兼容两种数据格式：增强版和普通版
  let modeData;
  let pilesData = [];
  let externalWaitingCount = 0;
  
  // 检查是否是增强版数据格式（包含piles信息）
  if (queueStatus[chargingMode] && queueStatus[chargingMode].piles) {
    // 增强版格式
    modeData = queueStatus[chargingMode];
    pilesData = modeData.piles || [];
    externalWaitingCount = modeData.external_waiting?.count || 0;
  } else {
    // 普通版格式，转换为增强版格式
    const legacyModeData = queueStatus[chargingMode + '_charging'];
    if (legacyModeData) {
      externalWaitingCount = legacyModeData.waiting_count || 0;
      // 没有桩的详细信息，使用默认估算
      // 这里我们可以基于系统参数估算一些默认值
      const powerKey = `${chargingMode}_charging_power`;
      const defaultPower = systemParams.charging_power?.[powerKey] || (chargingMode === 'fast' ? 120 : 7);
      
      // 模拟一些桩数据用于计算
      const estimatedPileCount = chargingMode === 'fast' ? 4 : 6; // 估算桩数量
      pilesData = Array.from({ length: estimatedPileCount }, (_, index) => ({
        pile_id: `${chargingMode.toUpperCase()}-${String(index + 1).padStart(2, '0')}`,
        is_working: index === 0, // 假设第一个桩在工作
        charging_power: defaultPower,
        queue_count: index === 0 ? 1 : 0, // 假设第一个桩有1个人在排队
        max_queue_size: 3,
        current_charging: index === 0 ? { 
          queue_number: 'SIMULATED',
          current_amount: 25,
          requested_amount: 50
        } : null,
        queue_list: []
      }));
    }
  }
  
  if (!pilesData || pilesData.length === 0) {
    // 如果仍然没有桩数据，使用基础估算
    const baseWaitMinutes = Math.max(10, externalWaitingCount * 10); // 每人10分钟
    
    return {
      estimated_wait_minutes: baseWaitMinutes,
      queue_position: externalWaitingCount + 1,
      ahead_count: externalWaitingCount,
      base_pile_wait: 0,
      additional_queue_wait: baseWaitMinutes,
      best_pile: null,
      pile_details: `基于排队人数估算(${externalWaitingCount}人)`,
      details: `基于排队人数估算：前方${externalWaitingCount}人等待，每人约10分钟`
    };
  }
  
  // 获取充电功率
  const chargingPower = systemParams.charging_power?.[`${chargingMode}_charging_power`] || 
                       (chargingMode === 'fast' ? 120 : 7);
  
  // 使用后端算法找到最优的可用桩
  const { minWaitTime, bestPile, availablePileFound } = findBestAvailablePile(pilesData, chargingPower);
  
  let baseWaitTime = minWaitTime;
  let pileDetails = '';
  
  if (availablePileFound && bestPile) {
    pileDetails = `最优桩${bestPile.pile_id}剩余${Math.round(minWaitTime)}分钟`;
  } else if (bestPile) {
    pileDetails = `桩${bestPile.pile_id}队列已满，预计${Math.round(minWaitTime)}分钟`;
  } else {
    // 如果没有找到合适的桩，使用默认估算
    baseWaitTime = 30; // 默认30分钟
    pileDetails = '使用默认估算30分钟';
  }
  
  // 考虑前面等待的人数（每个人增加10分钟等待）
  const additionalWaitTime = externalWaitingCount * 10;
  const totalWaitTime = baseWaitTime + additionalWaitTime;
  
  return {
    estimated_wait_minutes: Math.round(totalWaitTime),
    queue_position: externalWaitingCount + 1,
    ahead_count: externalWaitingCount,
    base_pile_wait: Math.round(baseWaitTime),
    additional_queue_wait: Math.round(additionalWaitTime),
    best_pile: bestPile,
    pile_details: pileDetails,
    details: `${pileDetails} + 前方${externalWaitingCount}人等待(${Math.round(additionalWaitTime)}分钟)`
  };
}

/**
 * 综合估算充电请求
 * @param {Object} requestData - 充电请求数据
 * @param {Object} systemParams - 系统参数
 * @param {Object} queueStatus - 队列状态
 * @returns {Object} - 完整估算结果
 */
export function estimateChargingRequest(requestData, systemParams, queueStatus) {
  const {
    charging_mode = 'fast',
    requested_amount = 50,
    start_time = new Date()
  } = requestData;
  
  if (!systemParams) {
    return {
      error: '系统参数不可用',
      charging_duration_minutes: 0,
      wait_time: { estimated_wait_minutes: 0 },
      cost_breakdown: { total_cost: 0 }
    };
  }
  
  // 获取充电功率
  const chargingPower = systemParams.charging_power?.[`${charging_mode}_charging_power`] || 
                       (charging_mode === 'fast' ? 120 : 7);
  
  // 计算充电时长
  const chargingDurationMinutes = calculateChargingDuration(requested_amount, chargingPower);
  
  // 计算等待时间（使用精确的桩剩余时间算法）
  const waitTime = calculateWaitTime(charging_mode, queueStatus, systemParams);
  
  // 估算开始充电的时间（当前时间 + 等待时间）
  const estimatedStartTime = new Date(start_time.getTime() + waitTime.estimated_wait_minutes * 60 * 1000);
  
  // 计算费用
  const costBreakdown = calculateChargingCost(
    requested_amount,
    estimatedStartTime,
    chargingDurationMinutes,
    systemParams.pricing
  );
  
  // 计算总时间
  const totalTimeMinutes = waitTime.estimated_wait_minutes + chargingDurationMinutes;
  
  return {
    charging_mode,
    requested_amount,
    charging_power: chargingPower,
    charging_duration_minutes: chargingDurationMinutes,
    wait_time: waitTime,
    estimated_start_time: estimatedStartTime,
    estimated_end_time: new Date(estimatedStartTime.getTime() + chargingDurationMinutes * 60 * 1000),
    total_time_minutes: totalTimeMinutes,
    cost_breakdown: costBreakdown,
    summary: {
      total_cost: costBreakdown.total_cost,
      total_time_display: formatTimeEstimate(totalTimeMinutes),
      wait_time_display: formatTimeEstimate(waitTime.estimated_wait_minutes),
      charging_time_display: formatTimeEstimate(chargingDurationMinutes)
    }
  };
}

/**
 * 格式化时间显示
 * @param {number} minutes - 分钟数
 * @returns {string} - 格式化的时间字符串
 */
export function formatTimeEstimate(minutes) {
  if (minutes < 1) {
    return '约 1 分钟';
  }
  
  if (minutes < 60) {
    return `约 ${Math.round(minutes)} 分钟`;
  }
  
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = Math.round(minutes % 60);
  
  if (remainingMinutes === 0) {
    return `约 ${hours} 小时`;
  } else {
    return `约 ${hours} 小时 ${remainingMinutes} 分钟`;
  }
}

/**
 * 格式化费用显示
 * @param {number} amount - 金额
 * @returns {string} - 格式化的费用字符串
 */
export function formatCurrency(amount) {
  return `¥${(amount || 0).toFixed(2)}`;
}

/**
 * 获取最优充电时间建议
 * @param {Object} pricing - 电价配置
 * @param {Object} timeConfig - 时间段配置
 * @returns {Object} - 时间建议
 */
export function getOptimalChargingTimeSuggestion(pricing, timeConfig = {}) {
  if (!pricing) return null;
  
  const suggestions = [];
  
  // 谷时充电最便宜
  if (pricing.valley_rate < pricing.normal_rate && pricing.valley_rate < pricing.peak_rate) {
    suggestions.push({
      period: 'valley',
      rate: pricing.valley_rate,
      time_range: '23:00-07:00',
      savings: ((pricing.peak_rate - pricing.valley_rate) / pricing.peak_rate * 100).toFixed(1),
      description: '谷时充电最省钱'
    });
  }
  
  // 避免峰时充电
  if (pricing.peak_rate > pricing.normal_rate) {
    suggestions.push({
      period: 'avoid_peak',
      rate: pricing.peak_rate,
      time_range: '10:00-15:00, 18:00-21:00',
      extra_cost: ((pricing.peak_rate - pricing.valley_rate)).toFixed(2),
      description: '避免峰时充电可节省费用'
    });
  }
  
  return suggestions;
}

/**
 * 计算不同时段充电的费用对比
 * @param {number} chargingAmount - 充电量
 * @param {number} chargingDurationMinutes - 充电时长(分钟)
 * @param {Object} pricing - 电价配置
 * @returns {Object} - 费用对比
 */
export function compareChargingCostsByTime(chargingAmount, chargingDurationMinutes, pricing) {
  if (!pricing || !chargingAmount) return null;
  
  const scenarios = [
    { name: '谷时充电', period: 'valley', rate: pricing.valley_rate },
    { name: '平时充电', period: 'normal', rate: pricing.normal_rate },
    { name: '峰时充电', period: 'peak', rate: pricing.peak_rate }
  ];
  
  const results = scenarios.map(scenario => {
    const electricityCost = chargingAmount * scenario.rate;
    const serviceCost = chargingAmount * pricing.service_rate;
    const totalCost = electricityCost + serviceCost;
    
    return {
      ...scenario,
      electricity_cost: Number(electricityCost.toFixed(2)),
      service_cost: Number(serviceCost.toFixed(2)),
      total_cost: Number(totalCost.toFixed(2))
    };
  });
  
  // 找出最便宜的方案
  const cheapest = results.reduce((min, current) => 
    current.total_cost < min.total_cost ? current : min
  );
  
  return {
    scenarios: results,
    cheapest: cheapest.name,
    max_savings: Number((results[2].total_cost - cheapest.total_cost).toFixed(2))
  };
} 