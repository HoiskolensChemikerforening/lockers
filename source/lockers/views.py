from django.contrib import messages
from django.contrib.auth.decorators import permission_required, login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse
from django.http import Http404
from django.shortcuts import redirect
from django.shortcuts import render, get_object_or_404

from lockers.email import send_activation_mail
from lockers.forms import RegisterExternalLockerUserForm, ConfirmOwnershipForm
from lockers.models import Locker, LockerUser, Ownership, LockerToken


def view_lockers(request, page=1):
    free_locker_list = Locker.objects.filter(owner__isnull=True).prefetch_related('owner')
    free_lockers = Locker.objects.filter(owner__isnull=True).count()
    paginator = Paginator(free_locker_list, 40)

    try:
        lockers = paginator.page(page)
    except PageNotAnInteger:
        lockers = paginator.page(1)
    except EmptyPage:
        lockers = paginator.page(paginator.num_pages)

    context = {
        "lockers": lockers,
        "free_lockers": free_lockers,
    }
    return render(request, 'lockers/list.html', context)


@login_required()
def my_lockers(request):
    try:
        locker_user = LockerUser.objects.get(user=request.user)
        lockers = locker_user.fetch_lockers()
    except LockerUser.DoesNotExist:
        lockers = []

    context = {
        'lockers': lockers
    }
    return render(request, 'lockers/mineskap.html', context)


@login_required()
def register_locker(request, number):
    # Fetch requested locker
    locker = Locker.objects.get(number=number)
    if not locker.is_free():
        # Locker was already taken
        raise Http404
    else:
        form_data = RegisterExternalLockerUserForm(request.POST or None)
        if form_data.is_valid():
            user = LockerUser.objects.get_or_create(user=request.user)

            # Create a new ownership for the user
            new_ownership = Ownership(locker=locker, user=user)
            if new_ownership.reached_limit():
                raise Http404

            new_ownership.save()

            # Create confirmation link object
            token = new_ownership.create_confirmation()
            send_activation_mail(user, token)
            messages.add_message(request, messages.SUCCESS,
                                 'Bokskapet er nesten reservert! '
                                 'En epost har blitt sendt til deg med videre instrukser for å bekrefte epostaddressen din.',
                                 extra_tags='Boskap - reservasjon')

            return redirect(reverse('frontpage:home'))

        context = {
            "form": form_data,
        }
        return render(request, 'lockers/registrer.html', context)


def activate_ownership(request, code):
    try:
        activator = LockerToken.objects.get(key=code)
    except ObjectDoesNotExist:
        messages.add_message(request, messages.ERROR,
                             'Aktiveringsnøkkelen er allerede brukt eller har utgått.',
                             extra_tags='Ugyldig nøkkel')
        raise Http404
    agreed_to_terms = ConfirmOwnershipForm(request.POST or None)
    if request.method == 'POST':
        if agreed_to_terms.is_valid():
            try:
                activator.activate()
            except ValidationError:
                messages.add_message(request, messages.ERROR,
                                     'Bokskapet ble reservert før du rakk å reservere det.',
                                     extra_tags='Bokskap - opptatt')
                return redirect(reverse('lockers:index'))

            messages.add_message(
                request, messages.SUCCESS, 'Bokskapet ble aktivert og er nå ditt =D',
                extra_tags='Fullført')

            return redirect(reverse('frontpage:home'))

    return render(request, 'lockers/confirm_locker.html', context={'form': agreed_to_terms})


@permission_required('lockers.delete_locker')
def manage_lockers(request):
    lockers = Locker.objects\
        .prefetch_related('indefinite_locker__user') \
        .prefetch_related('indefinite_locker__is_confirmed__exact=True') \
        .select_related('owner__user')

    context = {
        "request": request,
        "lockers": lockers
    }
    return render(request, 'lockers/administrer.html', context)


@permission_required('lockers.delete_locker')
def clear_locker(request, locker_number):
    locker = get_object_or_404(Locker, number=locker_number)
    if locker.owner:
        locker.clear()
        locker.save()

    return redirect(
        f'{reverse("lockers:administrate")}#locker{locker_number}'
    )