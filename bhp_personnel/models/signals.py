from datetime import datetime, time
import random
import string

from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User, Group
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_q.models import Schedule
from django_q.tasks import schedule
from edc_base.utils import get_utcnow
from edc_sms.classes import MessageSchedule

from . import Consultant, Contract, ContractExtension, Employee, Pi
from . import PerformanceAssessment, KeyPerformanceArea, Supervisor


@receiver(post_save, weak=False, sender=Employee,
          dispatch_uid='employee_on_post_save')
def employee_on_post_save(sender, instance, raw, created, **kwargs):
    if not raw:
        if created:

            try:
                created_user = User.objects.get(email=instance.email)
            except User.DoesNotExist:
                pwd = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits)
                              for _ in range(8))
                created_user = User.objects.create_user(username=instance.email,
                                         email=instance.email,
                                         password=pwd,
                                         first_name=instance.first_name,
                                         last_name=instance.last_name,
                                         is_staff=True,)
            send_employee_activation(instance)
            try:
                Supervisor.objects.get(first_name=instance.first_name,
                                       last_name=instance.last_name)
            except Supervisor.DoesNotExist:
                pass
            else:
                supervisor_group = Group.objects.get(name='Supervisor')
                supervisor_group.user_set.add(created_user)


def send_employee_activation(user):
    """
    Takes each user one by one and sending an email to each
    """

    reset_url = f"https://{get_current_site(request=None).domain}/password-reset/"  # current domain
    site_url = f"https://{get_current_site(request=None).domain}"  # current domain

    user_email = user.email  # user email
    frm = "bhp.se.dmc@gmail.com"  # from email
    subject = 'Time Sheet Activation Link'  # subject of the email
    message = f"""\
        Hi {user.first_name} {user.last_name},
        <br>
        <br>
        Your account for the BHP Timesheet System has been set up.
        The url to access the system is <a href="{site_url}" target="_blank">{site_url}</a>.
         <br>
         To activate your account, set the password first using the link below. 
        <br>
        <br>
        <a href="{reset_url}" target="_blank">Reset Password</a>
        <br>
        <br>
        Good Day 😃
        """

    msg = EmailMultiAlternatives(subject, message, frm, (user_email,))
    msg.content_subtype = 'html'
    print("Sending to : ", user.email)
    try:
        msg.send()
    except Exception as e:
        raise

def send_manager_on_employee_activation(user):
    mask = Employee.objects.get(id=user.id).supervisor_id
    supervisor_email = Supervisor.objects.get(id=str(mask)).email
    supervisor_firstname = Supervisor.objects.get(id=str(mask)).first_name
    supervisor_lastname = Supervisor.objects.get(id=str(mask)).last_name

    site_url = f"https://{get_current_site(request=None).domain}"

    frm = "admin@bhp.org.bw"
    subject = 'New Employee Contracting'
    message = f"""\
         Hi {supervisor_firstname} {supervisor_lastname},
        <br>
        <br>
        An new account for an employee has been set up.
        <br>
        <br>
        <a href="{site_url}" target="_blank">Visit Site</a>
        <br>
        <br>
        Good Day 😃
        """

    msg = EmailMultiAlternatives(subject, message, frm, (supervisor_email,))
    msg.content_subtype = 'html'
    print("Sending to : ", supervisor_email)
    try:
        msg.send()
    except Exception as e:
        raise

@receiver(post_save, weak=False, sender=Pi,
          dispatch_uid='pi_on_post_save')
def pi_on_post_save(sender, instance, raw, created, **kwargs):
    if not raw and created:
        User.objects.create_user(username=instance.
                                 first_name[0] + '' + instance.last_name,
                                 email=instance.email,
                                 password=instance.first_name + '@2020',
                                 first_name=instance.first_name,
                                 last_name=instance.last_name,
                                 is_staff=True,
                                 )


@receiver(post_save, weak=False, sender=Contract,
          dispatch_uid='contract_on_post_save')
def contract_on_post_save(sender, instance, raw, created, **kwargs):
    """
    Schedule email and sms reminder for 3 months before contract end
    date.
    """
    if not raw and created:
        create_appraisals(instance)
        create_key_performance_areas(job_description=instance.job_description)
        schedule_email_notification(instance)
        schedule_sms_notification(instance)


@receiver(post_save, weak=False, sender=ContractExtension,
          dispatch_uid='contractextension_on_post_save')
def contractextension_on_post_save(sender, instance, raw, created, **kwargs):
    """
    Reschedule an email and sms reminder for 3months before contract end
    date after extension.
    """
    if not raw and created:
        schedule_obj = get_schedule_obj(
            identifier=instance.contract.identifier)
        if schedule_obj:
            schedule_obj.delete()
        schedule_email_notification(instance, ext=True)
        schedule_sms_notification(instance, ext=True)


def create_key_performance_areas(job_description=None):
    """
    Create Key Performance Assessment for each KPA on the job description.
    """
    for job_description_kpa in job_description.jobdescriptionkpa_set.all():
        KeyPerformanceArea.objects.create(
            emp_identifier=job_description.identifier,
            contract=job_description.contract,
            kpa_nd_objective=job_description_kpa.key_performance_area,
            performance_indicators=job_description_kpa.kpa_performance_indicators,
            assessment_period_type='mid_year')

        KeyPerformanceArea.objects.create(
            emp_identifier=job_description.identifier,
            contract=job_description.contract,
            kpa_nd_objective=job_description_kpa.key_performance_area,
            performance_indicators=job_description_kpa.kpa_performance_indicators,
            assessment_period_type='contract_end')


def create_appraisals(instance=None):
    """
    Creates two appraisals on post save of a contract
    """
    PerformanceAssessment.objects.create(contract=instance,
                                         emp_identifier=instance.identifier,
                                         review='mid_year')
    PerformanceAssessment.objects.create(contract=instance,
                                         emp_identifier=instance.identifier,
                                         review='contract_end')


def schedule_email_notification(instance=None, ext=False):
    """
    Schedule email notification for contract expiration
    @param contract: instance of the contract
    """
    if instance:
        identifier = instance.contract.identifier if ext else instance.identifier
        end_date = (instance.end_date).strftime('%Y/%m/%d')
        user = get_user(identifier=identifier)

        schedule(
            'contract.tasks.contract_end_email_notification',
            user.first_name,
            user.last_name,
            user.email,
            user.supervisor.email,
            end_date,
            name=f'{user.identifier}{get_utcnow()}',
            schedule_type='O',
            next_run=reminder_datetime(instance=instance, ext=ext))


def schedule_sms_notification(instance=None, ext=False):
    """
    Schedule sms notification for contract expiration
    @param contract: instance of the contract
    """
    user = None
    if instance:
        identifier = instance.contract.identifier if ext else instance.identifier
        user = get_user(identifier=identifier)

    msg = (f'Dear+{user.first_name},+Please+be+aware+that+your+contract+'
           f'is+ending+on+the+{instance.end_date}.+Please+notify+your+'
           'supervisor+of+your+renewal+intent+within+the+month.+Have+a+good+'
           'day+:).')

    MessageSchedule().schedule_message(
        message_data=msg,
        recipient_number=user.cell,
        sms_type='reminder',
        schedule_datetime=reminder_datetime(instance=instance, ext=ext))


def reminder_datetime(instance=None, ext=False):
    """
    Returns datetime when the reminder should be scheduled.
    """
    if instance:
        duration = instance.contract.duration if ext else instance.duration
        reminder_date = None
        if duration == '6 Months':
            reminder_date = instance.end_date - relativedelta(months=1)
        elif duration == '1 Year':
            reminder_date = instance.end_date - relativedelta(months=2)
        elif duration == '2 Years':
            reminder_date = instance.end_date - relativedelta(months=3)
        return datetime.combine(reminder_date, datetime.strptime('10:00', '%H:%M').time())


def get_user(identifier=None):
    """
    Contract owner object getter
    @param identifier: unique identifier for the owner
    """
    try:
        return Employee.objects.get(identifier=identifier)
    except Employee.DoesNotExist:
        try:
            return Pi.objects.get(identifier=identifier)
        except Pi.DoesNotExist:
            try:
                return Consultant.objects.get(identifier=identifier)
            except Consultant.DoesNotExist:
                raise ValidationError(
                    f'Contract owner for identifier {identifier} does not exist.')


def get_schedule_obj(identifier=None):
    try:
        schedule_obj = Schedule.objects.get(name=f'{identifier}{get_utcnow()}')
    except ObjectDoesNotExist:
        return None
    else:
        return schedule_obj
