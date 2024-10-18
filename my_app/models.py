from django.db import models
from django.db.models import JSONField

class Event(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=100)
    description = models.TextField()
    date = models.DateTimeField()
    location = models.CharField(max_length=100)
    banner = models.ImageField(upload_to='events/banners/', blank=True, null=True)
    poster = models.ImageField(upload_to='events/posters/', blank=True, null=True)
    more_info_html = models.TextField(blank=True, null=True)
    form_id = models.IntegerField(blank=True, null=True)
    tickets_available = models.IntegerField(blank=True, null=True)
    payment_required = models.BooleanField(default=False) 
    event_amount = models.IntegerField(blank=True, null=True)
    multiple_members_required = models.BooleanField(default=False) 
    max_members = models.IntegerField(default=1)
    isDone = models.BooleanField(default=False)  

    def __str__(self):
        return self.title

class FormConfig(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=20, blank=True, null=True)
    fields = JSONField()

    def __str__(self):
        return self.title


class Ticket(models.Model):
    event_id = models.ForeignKey(Event, on_delete=models.DO_NOTHING, null=True)
    ticket_id = models.CharField(max_length=20, unique=True)
    enc_tk_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    uploaded_file = models.FileField(upload_to='events/uploads/', null=True, blank=True) 
    date_field = models.DateField(null=True, blank=True)
    is_paid = models.BooleanField(default=False) 
    payment_response = models.TextField(blank=True, null=True)
    no_of_members = models.IntegerField(default=1)
    ticket_data = models.JSONField() 
    isvalid =  models.SmallIntegerField(default=0)
    isused = models.SmallIntegerField(default=0) 
    check_in = models.DateTimeField(blank=True, null=True)
    check_out = models.DateTimeField(blank=True, null=True)
    sum = models.SmallIntegerField(default=0)


    def __str__(self):
        return f"{self.ticket_id}"