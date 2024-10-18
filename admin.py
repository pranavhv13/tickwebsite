from django.contrib import admin
from .models import Event, FormConfig, Ticket
# Register your models here.

admin.site.register(Event)
admin.site.register(FormConfig)
admin.site.register(Ticket)
