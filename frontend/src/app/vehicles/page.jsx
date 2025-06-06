'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Checkbox } from '@/components/ui/checkbox';
import { 
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { 
  Car, 
  Plus, 
  Edit, 
  Trash2, 
  MoreHorizontal,
  Battery,
  Star,
  StarOff 
} from 'lucide-react';
import { vehicleAPI } from '@/lib/vehicles';
import { toast } from 'sonner';
import { useForm } from 'react-hook-form';
import PageTransition, { containerVariants, itemVariants } from '@/components/layout/PageTransition';

export default function VehiclesPage() {
  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingVehicle, setEditingVehicle] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  
  // 添加删除确认弹窗状态
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [vehicleToDelete, setVehicleToDelete] = useState(null);

  const form = useForm({
    defaultValues: {
      license_plate: '',
      battery_capacity: '',
      vehicle_model: '',
      is_default: false
    }
  });

  useEffect(() => {
    fetchVehicles();
  }, []);

  const fetchVehicles = async () => {
    try {
      setLoading(true);
      const response = await vehicleAPI.getVehicles();
      if (response.success) {
        setVehicles(response.data);
      } else {
        toast.error('获取车辆列表失败');
      }
    } catch (error) {
      console.error('获取车辆列表失败:', error);
      toast.error('获取车辆列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (data) => {
    try {
      setSubmitting(true);
      const vehicleData = {
        ...data,
        battery_capacity: parseFloat(data.battery_capacity),
        is_default: data.is_default || false
      };

      let response;
      if (editingVehicle) {
        response = await vehicleAPI.updateVehicle(editingVehicle.id, vehicleData);
        toast.success('车辆信息更新成功');
      } else {
        response = await vehicleAPI.createVehicle(vehicleData);
        toast.success('车辆添加成功');
      }

      if (response.success) {
        await fetchVehicles();
        setDialogOpen(false);
        form.reset();
        setEditingVehicle(null);
      }
    } catch (error) {
      console.error('操作失败:', error);
      const errorMessage = error.response?.data?.error?.details || error.message;
      toast.error(editingVehicle ? `更新车辆信息失败: ${errorMessage}` : `添加车辆失败: ${errorMessage}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (vehicle) => {
    setEditingVehicle(vehicle);
    form.reset({
      license_plate: vehicle.license_plate,
      battery_capacity: vehicle.battery_capacity.toString(),
      vehicle_model: vehicle.vehicle_model || '',
      is_default: vehicle.is_default
    });
    setDialogOpen(true);
  };

  // 修改删除处理函数
  const handleDeleteClick = (vehicle) => {
    setVehicleToDelete(vehicle);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!vehicleToDelete) return;

    try {
      const response = await vehicleAPI.deleteVehicle(vehicleToDelete.id);
      if (response.success) {
        toast.success('车辆删除成功');
        await fetchVehicles();
      }
    } catch (error) {
      console.error('删除车辆失败:', error);
      toast.error('删除车辆失败');
    } finally {
      setDeleteDialogOpen(false);
      setVehicleToDelete(null);
    }
  };

  const handleSetDefault = async (vehicleId) => {
    try {
      const response = await vehicleAPI.setDefaultVehicle(vehicleId);
      if (response.success) {
        toast.success('默认车辆设置成功');
        await fetchVehicles();
      }
    } catch (error) {
      console.error('设置默认车辆失败:', error);
      toast.error('设置默认车辆失败');
    }
  };

  const openAddDialog = () => {
    setEditingVehicle(null);
    form.reset({
      license_plate: '',
      battery_capacity: '',
      vehicle_model: '',
      is_default: vehicles.length === 0
    });
    setDialogOpen(true);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">加载中...</p>
        </div>
      </div>
    );
  }

  return (
    <PageTransition>
      <div className="px-4 py-6 sm:px-0 bg-white dark:bg-black min-h-screen">
        <motion.div 
          className="mb-8 flex justify-between items-center"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div>
            <motion.h1 
              className="text-3xl font-bold"
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
            >
              车辆管理
            </motion.h1>
            <motion.p 
              className="mt-2 text-gray-600"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
            >
              管理您的车辆信息
            </motion.p>
          </div>
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Button onClick={openAddDialog} className="flex items-center">
              <Plus className="mr-2 h-4 w-4" />
              添加车辆
            </Button>
          </motion.div>
        </motion.div>

        {/* 车辆概览卡片 */}
        <motion.div 
          className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          <motion.div variants={itemVariants}>
            <Card className="hover:shadow-lg transition-shadow duration-300">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">总车辆数</CardTitle>
                <motion.div
                  animate={{ rotate: [0, 10, -10, 0] }}
                  transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                >
                  <Car className="h-4 w-4 text-muted-foreground" />
                </motion.div>
              </CardHeader>
              <CardContent>
                <motion.div 
                  className="text-2xl font-bold"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ duration: 0.5, delay: 0.5 }}
                >
                  {vehicles.length}
                </motion.div>
                <p className="text-xs text-muted-foreground">已注册车辆</p>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div variants={itemVariants}>
            <Card className="hover:shadow-lg transition-shadow duration-300">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">平均电池容量</CardTitle>
                <motion.div
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                >
                  <Battery className="h-4 w-4 text-muted-foreground" />
                </motion.div>
              </CardHeader>
              <CardContent>
                <motion.div 
                  className="text-2xl font-bold"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ duration: 0.5, delay: 0.6 }}
                >
                  {vehicles.length > 0 
                    ? (vehicles.reduce((sum, v) => sum + parseFloat(v.battery_capacity), 0) / vehicles.length).toFixed(1)
                    : 0
                  } kWh
                </motion.div>
                <p className="text-xs text-muted-foreground">所有车辆平均</p>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div variants={itemVariants}>
            <Card className="hover:shadow-lg transition-shadow duration-300">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">默认车辆</CardTitle>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                >
                  <Star className="h-4 w-4 text-muted-foreground" />
                </motion.div>
              </CardHeader>
              <CardContent>
                <motion.div 
                  className="text-2xl font-bold"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ duration: 0.5, delay: 0.7 }}
                >
                  {vehicles.find(v => v.is_default)?.license_plate || '未设置'}
                </motion.div>
                <p className="text-xs text-muted-foreground">当前默认车辆</p>
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>

        {/* 车辆列表 */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>车辆列表</CardTitle>
              <CardDescription>
                管理您的所有车辆信息，设置默认车辆用于快速充电
              </CardDescription>
            </CardHeader>
            <CardContent>
              {vehicles.length === 0 ? (
                <motion.div 
                  className="text-center py-8"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.6, delay: 0.5 }}
                >
                  <motion.div
                    whileHover={{ rotate: 360 }}
                    transition={{ duration: 0.5 }}
                  >
                    <Car className="mx-auto h-12 w-12 text-gray-400" />
                  </motion.div>
                  <motion.h3 
                    className="mt-2 text-sm font-medium text-gray-900"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.6 }}
                  >
                    暂无车辆
                  </motion.h3>
                  <motion.p 
                    className="mt-1 text-sm text-gray-500"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.7 }}
                  >
                    开始添加您的第一辆车
                  </motion.p>
                  <motion.div 
                    className="mt-6"
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.8, type: "spring", stiffness: 200 }}
                  >
                    <Button onClick={openAddDialog}>
                      <Plus className="mr-2 h-4 w-4" />
                      添加车辆
                    </Button>
                  </motion.div>
                </motion.div>
              ) : (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.5, delay: 0.5 }}
                >
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>车牌号</TableHead>
                        <TableHead>车辆型号</TableHead>
                        <TableHead>电池容量</TableHead>
                        <TableHead>状态</TableHead>
                        <TableHead>创建时间</TableHead>
                        <TableHead className="text-right">操作</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {vehicles.map((vehicle, index) => (
                        <motion.tr 
                          key={vehicle.id}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ duration: 0.3, delay: 0.6 + index * 0.1 }}
                          whileHover={{ backgroundColor: "rgba(59, 130, 246, 0.05)" }}
                          className="transition-colors"
                        >
                          <TableCell className="font-medium">
                            <div className="flex items-center">
                              {vehicle.license_plate}
                              {vehicle.is_default && (
                                <motion.div
                                  initial={{ scale: 0 }}
                                  animate={{ scale: 1 }}
                                  transition={{ type: "spring", stiffness: 300 }}
                                >
                                  <Star className="ml-2 h-4 w-4 text-yellow-500 fill-current" />
                                </motion.div>
                              )}
                            </div>
                          </TableCell>
                          <TableCell>{vehicle.vehicle_model || '未设置'}</TableCell>
                          <TableCell>{vehicle.battery_capacity} kWh</TableCell>
                          <TableCell>
                            <Badge variant={vehicle.is_default ? 'default' : 'secondary'}>
                              {vehicle.is_default ? '默认车辆' : '普通车辆'}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {new Date(vehicle.created_at).toLocaleDateString('zh-CN')}
                          </TableCell>
                          <TableCell className="text-right">
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <motion.div
                                  whileHover={{ scale: 1.1 }}
                                  whileTap={{ scale: 0.9 }}
                                >
                                  <Button variant="ghost" className="h-8 w-8 p-0">
                                    <span className="sr-only">打开菜单</span>
                                    <MoreHorizontal className="h-4 w-4" />
                                  </Button>
                                </motion.div>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem onClick={() => handleEdit(vehicle)}>
                                  <Edit className="mr-2 h-4 w-4" />
                                  编辑
                                </DropdownMenuItem>
                                {!vehicle.is_default && (
                                  <DropdownMenuItem onClick={() => handleSetDefault(vehicle.id)}>
                                    <Star className="mr-2 h-4 w-4" />
                                    设为默认
                                  </DropdownMenuItem>
                                )}
                                <DropdownMenuItem 
                                  onClick={() => handleDeleteClick(vehicle)}
                                  className="text-red-600"
                                >
                                  <Trash2 className="mr-2 h-4 w-4" />
                                  删除
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </motion.tr>
                      ))}
                    </TableBody>
                  </Table>
                </motion.div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* 添加/编辑车辆对话框 */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>
                {editingVehicle ? '编辑车辆信息' : '添加新车辆'}
              </DialogTitle>
              <DialogDescription>
                {editingVehicle ? '修改车辆信息' : '填写车辆基本信息，添加到您的车辆列表'}
              </DialogDescription>
            </DialogHeader>
            <Form {...form}>
              <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
                <FormField
                  control={form.control}
                  name="license_plate"
                  rules={{ 
                    required: '请输入车牌号',
                    pattern: {
                      value: /^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领A-Z]{1}[A-Z]{1}[A-Z0-9]{4}[A-Z0-9挂学警港澳]{1}$/,
                      message: '请输入正确的车牌号格式'
                    }
                  }}
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>车牌号</FormLabel>
                      <FormControl>
                        <Input placeholder="如：京A12345" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="vehicle_model"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>车辆型号（可选）</FormLabel>
                      <FormControl>
                        <Input placeholder="如：特斯拉 Model 3" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="battery_capacity"
                  rules={{ 
                    required: '请输入电池容量',
                    min: { value: 10, message: '电池容量不能小于10kWh' },
                    max: { value: 200, message: '电池容量不能大于200kWh' }
                  }}
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>电池容量 (kWh)</FormLabel>
                      <FormControl>
                        <Input 
                          type="number" 
                          step="0.1"
                          placeholder="如：75.5" 
                          {...field} 
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="is_default"
                  render={({ field }) => (
                    <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                      <FormControl>
                        <Checkbox
                          checked={field.value}
                          onCheckedChange={field.onChange}
                          disabled={editingVehicle?.is_default}
                        />
                      </FormControl>
                      <div className="space-y-1 leading-none">
                        <FormLabel>
                          设为默认车辆
                        </FormLabel>
                        <p className="text-sm text-muted-foreground">
                          默认车辆将用于快速充电预约
                        </p>
                      </div>
                    </FormItem>
                  )}
                />

                <div className="flex justify-end space-x-2 pt-4">
                  <Button 
                    type="button" 
                    variant="outline" 
                    onClick={() => setDialogOpen(false)}
                    disabled={submitting}
                  >
                    取消
                  </Button>
                  <Button type="submit" disabled={submitting}>
                    {submitting ? '处理中...' : (editingVehicle ? '更新' : '添加')}
                  </Button>
                </div>
              </form>
            </Form>
          </DialogContent>
        </Dialog>

        {/* 删除确认对话框 */}
        <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>确认删除车辆</AlertDialogTitle>
              <AlertDialogDescription>
                您确定要删除车辆 <span className="font-semibold">{vehicleToDelete?.license_plate}</span> 吗？
                此操作无法撤销，删除后该车辆的所有相关数据将被永久移除。
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>取消</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDeleteConfirm}
                className="bg-red-600 hover:bg-red-700 focus:ring-red-600 text-white"
              >
                确认删除
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </PageTransition>
  );
} 