from datetime import datetime
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q, F, CheckConstraint, UniqueConstraint, Count
from django.core.validators import RegexValidator
from django.utils import timezone
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError

class User(AbstractUser):
    """
    Расширяем стандартную модель User добавив роль, телефон и адрес
    """
    ROLES = (
        ('CL', 'Клиент'),
        ('TR', 'Тренер'),
        ('AD', 'Админ'),
    )

    role = models.CharField(max_length=2, choices=ROLES)
    phone = models.CharField(
        max_length=20, 
        blank=True, 
        validators=[
            RegexValidator(
                regex=r'^\+7[67]\d{9}$',
                message="Телефонный номер должен быть в формате : '+76XXXXXXXXX' или '+77XXXXXXXXX'."
            )
        ]
    ) # формат телефонного номера в Казахстане 
    address = models.CharField(max_length=100, blank=True) # адрес пользователя


    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.username})'
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'



class Room(models.Model):
    """
    Room - залы фитнес-клуба.
    """
    ROOM_TYPES = (
        ('TR', 'Тренажерный зал'),
        ('GR', 'Зал для групповых занятий'),
        ('SW', 'Бассейн'),
        ('YR', 'Йога-зал'),
    )
    room_type = models.CharField(max_length=2, choices=ROOM_TYPES)
    name = models.CharField(max_length=100, null=True) # название зала
    capacity = models.PositiveIntegerField() # допустимое количество человек в зале

    @property
    def available_seats(self):
        """
        Свойство возвращает количество свободных мест в зале.
        """
        return self.capacity - self.trainings.aggregate(bookings_count=Count('bookings'))['bookings_count']

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Зал'
        verbose_name_plural = 'Залы'


class WorkSchedule(models.Model):
    """
    WorkSchedule - график работы тренера.
    """
    start_time = models.TimeField() # время начала работы
    end_time = models.TimeField() # время окончания работы
    break_start = models.TimeField() # время начала перерыва
    break_end = models.TimeField() # время окончания перерыва


    class Meta:
        constraints = [
            CheckConstraint(check=Q(start_time__lt=F('end_time')), name='api_workschedule_start_time_lt_end_time'),
            CheckConstraint(
                check=Q(end_time__lt=F('break_start')) | Q(start_time__gt=F('break_end')),
                name='no_work_during_break'),
        ]

    def is_available(self, start_time, end_time):
        """
        Проверяет, доступен ли тренер в указанное время.
        start_time - время начала тренировки.
        end_time - время окончания тренировки.
        """
        return self.start_time <= start_time and self.end_time >= end_time

    def __str__(self):
        return f"{self.start_time} - {self.end_time}"
    
    class Meta:
        verbose_name = 'Рабочий график'
        verbose_name_plural = 'Рабочие графики'



class Trainer(models.Model):
    """
    Trainer - тренеры фитнес-клуба.
    """
    GENDERS = (
        ('M', 'Мужчина'),
        ('F', 'Женщина'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='trainer_profile')
    rooms = models.ManyToManyField(Room, related_name='trainers')
    gender = models.CharField(max_length=1, choices=GENDERS)
    work_schedule = models.ForeignKey(WorkSchedule, on_delete=models.SET_NULL, null=True) # график работы тренера

    def is_available(self, start_time, end_time):
        """
        Проверяет, доступен ли тренер отправившему запросу в указанное время.
        start_time - время начала тренировки.
        end_time - время окончания тренировки.
        """
        if self.work_schedule is None:
            return False
        return self.work_schedule.is_available(start_time, end_time)
    def add_room(self, room):
        """
        Добавляет зал в список залов, в которых работает тренер.
        """
        self.rooms.add(room)

    def remove_room(self, room):
        """
        Удаляет зал из списка залов, в которых работает тренер.
        """
        self.rooms.remove(room)
    
    class Meta:
        verbose_name = 'Тренер'
        verbose_name_plural = 'Тренеры'

    def __str__(self):
        return f'{self.user.first_name} {self.user.last_name}'
    

class GroupTrainingType(models.Model):
    """
    GroupTrainingType - типы групповых тренировок.
    """
    name = models.CharField(max_length=100)  # Название вида тренировки

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Тип групповой тренировки'
        verbose_name_plural = 'Типы групповых тренировок'


class Training(models.Model):
    """
    Training - тренировки фитнес-клуба.
    """
    TRAINING_TYPES = (
        ('GT', 'Групповые занятия'), # занятие в группе: помогает клиентам в зале или проводит занятие в группе
        ('PT', 'Персональные тренировки'), # тренировка с тренером наедине
        ('SW', 'Свободная тренировка'), # свободное занятие без тренера
    )
    trainer = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name='trainer_trainings', null=True, blank=True, limit_choices_to={'user__role': 'TR'})
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='room_trainings')
    training_type = models.CharField(max_length=2, choices=TRAINING_TYPES) # тип тренировки
    group_training_type = models.ForeignKey(GroupTrainingType, on_delete=models.SET_NULL, null=True, blank=True)
    start_time = models.TimeField() # время начала тренировки
    end_time = models.TimeField() # время окончания тренировки

    class Meta:
        verbose_name = 'Тренировка'
        verbose_name_plural = 'Тренировки'
        constraints = [
            CheckConstraint(check=Q(start_time__lt=F('end_time')), name='api_training_start_time_lt_end_time'),
        ]

    @classmethod
    def get_available_trainings(cls, start_time): 
        """
        Возвращает все доступные тренировки после указанного времени.
        cls - ссылка на класс.
        start_time - время начала тренировки.
        """
        return cls.objects.filter(
            Q(start_time__gte=start_time) &  # время начала тренировки после указанного времени
            ~Q(bookings__booking_time__range=(F('start_time'), F('end_time'))) # нет бронирований в это время
        ).annotate(
            bookings_count=Count('bookings') # количество бронирований
        ).filter(
            bookings_count__lt=F('room__capacity') # количество бронирований меньше вместимости зала
        )


    def can_book(self, booking_time):
        """
        Проверяет, можно ли забронировать тренировку в указанное время.
        booking_time - время бронирования.
        """
        if isinstance(booking_time, str):
            booking_time = datetime.fromisoformat(booking_time).time()
        bookings_count = Booking.objects.filter(
            training=self, # тренировка
            booking_time__hour__range=(self.start_time.hour, self.end_time.hour) # время тренировки
        ).count() # количество бронирований

        work_schedule = self.trainer.work_schedule

        if work_schedule.break_start <= booking_time <= work_schedule.break_end:
            return False
        elif self.training_type == 'GT':  # Групповые занятия
            # Проверяем, доступен ли тренер в указанное время
            if not self.trainer.is_available(self.start_time, self.end_time):
                return False
            # Проверяем, проводит ли тренер в это время такую же групповую тренировку
            same_group_trainings = Training.objects.filter(
                trainer=self.trainer,
                group_training_type=self.group_training_type,
                start_time__lte=self.start_time,
                end_time__gte=self.end_time
            )
            if not same_group_trainings.exists():
                return False
            # Проверяем количество свободных мест в зале
            return bookings_count < self.room.capacity
        elif self.training_type == 'PT':  # Персональные тренировки
            # Проверяем доступность тренера и количество бронирований в это время. 
            # Персональные тренировки не могут быть забронированы, если уже есть бронирование в это время.
            if bookings_count > 0 or not self.trainer:
                return False
            if not self.trainer.is_available(self.start_time, self.end_time):
                return False
        elif self.training_type == 'SW':  # Свободная тренировка
            # Для свободных тренировок проверяем количество свободных мест в зале
            return bookings_count < self.room.capacity

        return bookings_count < self.room.capacity

    
    def __str__(self):
        training_type_dict = dict(Training.TRAINING_TYPES)
        return f"{self.trainer if self.trainer else 'Без тренера'} - {self.room} - {training_type_dict.get(self.training_type, 'Неизвестный тип')}"
        
    
    def clean(self): 
        if self.training_type == 'GT' and not self.group_training_type:
            raise ValidationError("Групповые тренировки должны иметь тип группы.")
        if self.training_type != 'GT' and self.group_training_type:
            raise ValidationError("Тип группы должен быть указан только для групповых тренировок.")
        if self.trainer and self.room and self.room not in self.trainer.rooms.all():
            raise ValidationError("Тренер не работает в выбранном зале.")
        if self.trainer and self.training_type == 'SW':
            raise ValidationError("Свободная тренировка не может быть выбрана, если выбран тренер.")


class Booking(models.Model):
    """
    Booking - бронирование тренировок.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_bookings', limit_choices_to={'role': 'CL'})
    training = models.ForeignKey(Training, on_delete=models.CASCADE, related_name='training_bookings', null=True, blank=True)
    booking_time = models.DateTimeField(default=timezone.now) 

    class Meta:
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'
        constraints = [
            UniqueConstraint(fields=['user', 'training'], name='unique_booking_per_user'),
        ]

    def clean(self):
        super().clean()  # переопределяем метод clean чтобы переопределить его поведение иначе он вызовет ошибку когда ValidationError
        booking_time_str = str(self.booking_time) if self.booking_time else None
        if booking_time_str and not self.training.can_book(booking_time_str):
            raise ValidationError('Уже есть бронирование в это время или тренер не доступен в это время') 
        
    def __str__(self):
        return f"Клиент: {self.user.username} - Тренер: {self.training} на {self.booking_time.strftime('%Y-%m-%d %H:%M')}"


@receiver(post_save, sender=User)
def create_or_update_trainer_profile(sender, instance, created, **kwargs):
    # Создаем профиль тренера при создании пользователя с ролью 'TR'
    # или обновляем профиль при изменении роли на 'TR'.
    if instance.role == 'TR':
        Trainer.objects.get_or_create(user=instance)

@receiver(pre_save, sender=Booking)
def check_booking_time(sender, instance, **kwargs):
    booking_time_str = str(instance.booking_time) if instance.booking_time else None
    if booking_time_str and not instance.training.can_book(booking_time_str):
        raise ValidationError('Уже есть бронирование в это время или тренер не доступен в это время')
