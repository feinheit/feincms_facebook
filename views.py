import logging
from feinheit.newsletter.models import Subscription
from feinheit.translations import short_language_code
from facebook.utils import parseSignedRequest
from django.conf import settings
from django.shortcuts import render_to_response, redirect
from django.contrib.sites.models import Site
from feincms.content.application.models import reverse
from django.template.context import RequestContext
logger = logging.getLogger(__name__)

def newsletter(request):

    def subscribe(registration):
        logger.debug('registration: %s' %registration)
        subscriber, created = Subscription.objects.get_or_create(email=registration['email'])
        subscriber.salutation = 'f' if registration['gender'] == 'female' else 'm'
        subscriber.first_name, subscriber.last_name = registration['first_name'], registration['last_name']
        subscriber.city = registration['location']['name']
        subscriber.language = short_language_code()
        subscriber.ip = request.META['REMOTE_ADDR']
        subscriber.activation_code = registration['facebook_id']
        subscriber.email = registration['email']
        subscriber.active = True
        subscriber.save()
        if getattr(settings, 'CLEVERREACH_GROUPS', False):
            """ Copy cleverreach.py to your project folder to make adjustments. """
            try: 
                cleverreach = __import__('%s.cleverreach' %settings.APP_MODULE)
                from cleverreach import insert_new_user, deactivate_user
            except ImportError:
                from feinheit.cleverreach import insert_new_user, deactivate_user  # TODO: Check this. Doesn't work on server.
            forms = getattr(settings, 'CLEVERREACH_FORMS', None)
            form_id = forms[short_language_code()] if forms else None    
            groups = getattr(settings, 'CLEVERREACH_GROUPS')
            group_id = groups['nl_%s' %short_language_code()]
            logger.info('sending: %s' %registration)
            status = insert_new_user(registration, group_id, activated=True, sendmail=False, form_id=form_id)
            logger.debug('Cleverreach response: %s' %status)
    
    if request.method == 'POST' and request.POST.get('signed_request', None):
        signed_request = parseSignedRequest(request.POST.get('signed_request'))
        logger.debug('newsletter signed_request: %s' %signed_request)
        signed_request['registration'].update({'facebook_id': signed_request['user_id']})
        subscribe(signed_request['registration'])
        return redirect('newsletter_thanks')
        
    site = Site.objects.all()[0].domain
    context = {'app_id': settings.FACEBOOK_APP_ID,
               'redirect_uri': 'http://%s%s' %(site, reverse('newsletter_registration'))}
    return render_to_response('content/facebook/register.txt', context, 
                              RequestContext(request))
