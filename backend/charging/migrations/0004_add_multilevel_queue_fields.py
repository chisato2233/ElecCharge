# Generated by Django 4.2.21 on 2025-06-06 10:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('charging', '0003_chargingrequest_vehicle_chargingsession_vehicle'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='chargingrequest',
            name='queue_position',
        ),
        migrations.AddField(
            model_name='chargingpile',
            name='charging_power',
            field=models.FloatField(default=120.0, help_text='快充通常120kW，慢充7kW', verbose_name='充电功率(kW)'),
        ),
        migrations.AddField(
            model_name='chargingpile',
            name='estimated_remaining_time',
            field=models.IntegerField(default=0, verbose_name='预计剩余时间(分钟)'),
        ),
        migrations.AddField(
            model_name='chargingpile',
            name='max_queue_size',
            field=models.IntegerField(default=3, verbose_name='桩队列最大容量'),
        ),
        migrations.AddField(
            model_name='chargingrequest',
            name='external_queue_position',
            field=models.IntegerField(default=0, verbose_name='外部等候区位置'),
        ),
        migrations.AddField(
            model_name='chargingrequest',
            name='pile_queue_position',
            field=models.IntegerField(default=0, verbose_name='桩队列位置'),
        ),
        migrations.AddField(
            model_name='chargingrequest',
            name='queue_level',
            field=models.CharField(choices=[('external_waiting', '外部等候区'), ('pile_queue', '充电桩队列'), ('charging', '正在充电'), ('completed', '已完成')], default='external_waiting', max_length=20, verbose_name='队列层级'),
        ),
        migrations.AlterField(
            model_name='chargingrequest',
            name='charging_pile',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='charging.chargingpile', verbose_name='分配的充电桩'),
        ),
        migrations.AlterField(
            model_name='chargingrequest',
            name='estimated_wait_time',
            field=models.IntegerField(default=0, verbose_name='预计等待时间(分钟)'),
        ),
        migrations.AlterField(
            model_name='notification',
            name='type',
            field=models.CharField(choices=[('queue_update', '排队更新'), ('charging_start', '开始充电'), ('charging_complete', '充电完成'), ('pile_fault', '充电桩故障'), ('queue_transfer', '转入桩队列')], max_length=20),
        ),
        migrations.AddConstraint(
            model_name='chargingrequest',
            constraint=models.UniqueConstraint(condition=models.Q(('current_status__in', ['waiting', 'charging'])), fields=('vehicle',), name='unique_active_request_per_vehicle'),
        ),
    ]
