from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Room, WorkSchedule, Trainer, GroupTrainingType, Training, Booking

class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {'fields': ('role', 'phone', 'address')}),
    )
    list_display = ['username', 'email', 'is_staff', 'is_active', 'role', 'phone', 'address']
    search_fields = ['username', 'email']
    list_filter = ['is_staff', 'is_active', 'role']

class RoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'capacity']

class WorkScheduleAdmin(admin.ModelAdmin):
    list_filter = ['start_time']
    list_display = ['start_time', 'end_time', 'break_start', 'break_end']

class TrainerAdmin(admin.ModelAdmin):
    search_fields = ['user__username']
    list_display = ['user', 'gender', 'work_schedule']

class GroupTrainingTypeAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_display = ['name']

class TrainingAdmin(admin.ModelAdmin):
    list_filter = ['training_type', 'room', 'trainer']
    list_display = ['trainer', 'room', 'training_type', 'start_time', 'end_time']

class BookingAdmin(admin.ModelAdmin):
    list_filter = ['user', 'training']
    list_display = ['user', 'training', 'booking_time']

admin.site.register(User, UserAdmin)
admin.site.register(Room, RoomAdmin)
admin.site.register(WorkSchedule, WorkScheduleAdmin)
admin.site.register(Trainer, TrainerAdmin)
admin.site.register(GroupTrainingType, GroupTrainingTypeAdmin)
admin.site.register(Training, TrainingAdmin)
admin.site.register(Booking, BookingAdmin)