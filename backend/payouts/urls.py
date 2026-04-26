from django.urls import path
from . import views

urlpatterns = [
    path("merchants/", views.MerchantListView.as_view(), name="merchant-list"),
    path("merchants/<uuid:merchant_id>/", views.MerchantDashboardView.as_view(), name="merchant-dashboard"),
    path("merchants/<uuid:merchant_id>/ledger/", views.LedgerView.as_view(), name="ledger"),
    path("merchants/<uuid:merchant_id>/payouts/", views.PayoutListCreateView.as_view(), name="payout-list-create"),
    path("merchants/<uuid:merchant_id>/payouts/<uuid:payout_id>/", views.PayoutDetailView.as_view(), name="payout-detail"),
    path("merchants/<uuid:merchant_id>/invariant/", views.BalanceInvariantCheckView.as_view(), name="balance-invariant"),
]
