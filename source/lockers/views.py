from django.contrib import messages
from django.contrib.auth.decorators import permission_required, login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.views import View
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.shortcuts import render, get_object_or_404

from lockers.forms import ConfirmOwnershipForm
from lockers.models import Locker, LockerUser, Ownership, LockerToken


class LockerView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        try:
            user_is_authenticated = request.user.is_authenticated()
        except TypeError:
            user_is_authenticated = request.user.is_authenticated
        if user_is_authenticated:
            return self.view_register_locker(request)
        return self.login(request)

    def login(self, request):
        free_lockers = Locker.objects.filter(owner__isnull=True).count()
        context = {"free_lockers": free_lockers}
        return render(request, "lockers/login.html", context)

    def view_register_locker(self, request, page=1):
        free_locker_list = Locker.objects.filter(owner__isnull=True).prefetch_related("owner")
        free_lockers = Locker.objects.filter(owner__isnull=True).count()
        paginator = Paginator(free_locker_list, 40)

        try:
            lockers = paginator.page(page)
        except PageNotAnInteger:
            lockers = paginator.page(1)
        except EmptyPage:
            lockers = paginator.page(paginator.num_pages)

        context = {"lockers": lockers, "free_lockers": free_lockers}
        return render(request, "lockers/list.html", context)


def index(request, page=1):
    """
    free_locker_list = Locker.objects.filter(owner__isnull=True).prefetch_related("owner")
    free_lockers = Locker.objects.filter(owner__isnull=True).count()
    paginator = Paginator(free_locker_list, 40)

    try:
        lockers = paginator.page(page)
    except PageNotAnInteger:
        lockers = paginator.page(1)
    except EmptyPage:
        lockers = paginator.page(paginator.num_pages)

    context = {"lockers": lockers, "free_lockers": free_lockers}

    template_name = 'my_app/my_template.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated():
            return redirect('my-other-view')
        return super(index, self).dispatch(request, *args, **kwargs)
    return render(request, "lockers/login.html", context)
    """


@login_required()
def my_lockers(request):
    try:
        locker_user = LockerUser.objects.get(user=request.user)
        lockers = locker_user.fetch_lockers()
    except LockerUser.DoesNotExist:
        lockers = []

    context = {"lockers": lockers}
    return render(request, "lockers/mineskap.html", context)


@login_required()
def register_locker(request, number):
    # Fetch requested locker
    locker = Locker.objects.get(number=number)
    if not locker.is_free():
        # Locker was already taken
        raise Http404
    else:
        form_data = ConfirmOwnershipForm(request.POST or None)
        if form_data.is_valid():
            user = LockerUser.objects.get(user=request.user)

            # Create a new ownership for the user
            new_ownership = Ownership(locker=locker, user=user)
            if new_ownership.reached_limit():
                raise Http404

            new_ownership.save()

            # Create confirmation link object
            token = new_ownership.create_confirmation()
            token.activate()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Skapet er ditt!",
                """
                Du har nå reservert skapet frem til sommeren.
                Du vil bli bedt om å forlenge statusen når den tid kommer.
                """,
            )
            return redirect(reverse("lockers:index"))

        context = {"form": form_data}
        return render(request, "lockers/confirm_locker.html", context)


def activate_ownership(request, code):
    try:
        activator = LockerToken.objects.get(key=code)
    except ObjectDoesNotExist:
        messages.add_message(
            request,
            messages.ERROR,
            "Aktiveringsnøkkelen er allerede brukt eller har utgått.",
            extra_tags="Ugyldig nøkkel",
        )
        raise Http404
    agreed_to_terms = ConfirmOwnershipForm(request.POST or None)
    if request.method == "POST":
        if agreed_to_terms.is_valid():
            try:
                activator.activate()
            except ValidationError:
                messages.add_message(
                    request,
                    messages.ERROR,
                    "Bokskapet ble reservert før du rakk å reservere det.",
                    extra_tags="Bokskap - opptatt",
                )
                return redirect(reverse("lockers:index"))

            messages.add_message(
                request, messages.SUCCESS, "Bokskapet ble aktivert og er nå ditt =D", extra_tags="Fullført"
            )

            return redirect(reverse("lockers:index"))

    return render(request, "lockers/confirm_locker.html", context={"form": agreed_to_terms})


@permission_required("lockers.delete_locker")
def manage_lockers(request):
    lockers = (
        Locker.objects.prefetch_related("indefinite_locker__user")
        .prefetch_related("indefinite_locker__is_confirmed__exact=True")
        .select_related("owner__user")
    )

    context = {"request": request, "lockers": lockers}
    return render(request, "lockers/administrer.html", context)


@permission_required("lockers.delete_locker")
def clear_locker(request, locker_number):
    locker = get_object_or_404(Locker, number=locker_number)
    if locker.owner:
        locker.clear()
        locker.save()

    return redirect(f'{reverse("lockers:administrate")}#locker{locker_number}')
