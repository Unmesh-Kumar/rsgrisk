import logging
from typing import Any, Dict, Tuple

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import CompanySearchForm
from esg.exceptions import ESGServiceError
from esg.history import SearchHistoryRepository
from esg.services import ESGService

logger = logging.getLogger(__name__)


def _handle_company_search(user_id: int, company_name: str) -> Tuple[Dict[str, Any], bool]:
    service = ESGService()
    result, from_cache = service.get_company_esg_profile(company_name)
    repository = SearchHistoryRepository()
    repository.record_search(user_id=user_id, company_name=company_name)
    return result, from_cache


@login_required
def dashboard_view(request: HttpRequest) -> HttpResponse:
    repository = SearchHistoryRepository()
    recent_searches = repository.get_recent_searches(user_id=request.user.id, limit=10)

    searched_company: str | None = None

    if request.method == 'POST':
        form = CompanySearchForm(request.POST)
        if form.is_valid():
            searched_company = form.cleaned_data['company_name']
    else:
        preset_company = request.GET.get('company')
        if preset_company:
            searched_company = preset_company
            form = CompanySearchForm(initial={'company_name': preset_company})
        else:
            form = CompanySearchForm()

    context: Dict[str, Any] = {
        'form': form,
        'recent_searches': recent_searches,
    }

    if searched_company:
        try:
            result, from_cache = _handle_company_search(request.user.id, searched_company)
            context['result'] = result
            context['from_cache'] = from_cache
        except ESGServiceError as exc:
            logger.exception('ESG service error for company %s', searched_company)
            messages.error(request, str(exc))
        except Exception as exc:  # noqa: BLE001
            logger.exception('Unexpected error while processing company %s', searched_company)
            messages.error(request, 'An unexpected error occurred while processing the request.')

    return render(request, 'dashboard/dashboard.html', context)


@login_required
def redirect_to_dashboard(_: HttpRequest) -> HttpResponse:
    return redirect(reverse('dashboard:home'))
