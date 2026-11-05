import hashlib
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.cache import cache
from django.core.exceptions import ValidationError
class LimitedAdminAuthenticationForm(AdminAuthenticationForm):
    def clean(self):
        username=self.data.get('username','')[:200]
        key='admin-login-'+hashlib.sha256((self.request.META.get('REMOTE_ADDR','')+':'+username).encode()).hexdigest()
        count=cache.get(key,0)
        if count>=10:raise ValidationError('Слишком много попыток. Подождите 5 минут.')
        try:result=super().clean()
        except ValidationError:
            cache.set(key,count+1,300)
            raise
        cache.delete(key)
        return result
