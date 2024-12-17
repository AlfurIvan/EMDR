from datetime import datetime
from datetime import timedelta
from io import BytesIO

from django.db.models import Q, Count
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.utils.timezone import now
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, extend_schema_view, OpenApiResponse, \
    inline_serializer
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from rest_framework import status, serializers, permissions
from rest_framework.exceptions import NotFound
from rest_framework.fields import CharField
from rest_framework.generics import RetrieveUpdateAPIView, ListAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import AlertFilter
from .models import Alert, Endpoint, Customer, MitigationStrategy
from .permissions import IsCustomer, IsAnalyst, is_analyst, IsAuthenticatedWithMFA
from .serializers import AlertSerializer, MitigationStrategySerializer, EndpointSerializer, AlertCreateSerializer, \
    AlertMitigationSelectSerializer, EndpointCustSerializer


@extend_schema(
    request=AlertCreateSerializer,
    responses={201: AlertSerializer},
    description="Create a new alert and return its details."
)
class ReceiveAlertView(CreateAPIView):
    """Receiving object, creating of the new Alert if data is valid"""
    queryset = Alert.objects.all()
    serializer_class = AlertCreateSerializer
    permission_classes = [IsAuthenticatedWithMFA]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        alert = serializer.save()
        response_serializer = AlertSerializer(alert)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="status",
            description="Filter by alert status. Choices: open, validated, resolved.",
            required=False,
            type=OpenApiTypes.STR,
        ),
        OpenApiParameter(
            name="closure_code",
            description="Filter by closure code. Choices: NA, TP, FP, TPNM.",
            required=False,
            type=OpenApiTypes.STR,
        ),
        OpenApiParameter(
            name="source",
            description="Filter by source (ID of the source).",
            required=False,
            type=OpenApiTypes.INT,
        ),
        OpenApiParameter(
            name="timestamp_before",
            description="Filter alerts created before the specified timestamp (ISO 8601 format).",
            required=False,
            type=OpenApiTypes.DATETIME,
        ),
        OpenApiParameter(
            name="timestamp_after",
            description="Filter alerts created after the specified timestamp (ISO 8601 format).",
            required=False,
            type=OpenApiTypes.DATETIME,
        ),
    ],
    description="Retrieve a paginated list of alerts with optional filtering.",
    responses={200: AlertSerializer(many=True)},
)
class AlertListView(ListAPIView):
    """Alert List representation for Analysts"""

    permission_classes = (IsAuthenticatedWithMFA, IsAnalyst)
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    filterset_class = AlertFilter

    def get_queryset(self):
        queryset = super().get_queryset()
        return self.filter_queryset_by_timestamp(queryset)

    def filter_queryset_by_timestamp(self, queryset):
        before = self.request.query_params.get('timestamp_before')
        after = self.request.query_params.get('timestamp_after')

        if before:
            queryset = queryset.filter(timestamp__lte=before)

        if after:
            queryset = queryset.filter(timestamp__gte=after)
        return queryset


class CustomerAlertListView(AlertListView):
    """List representation of Alerts for Customer."""
    permission_classes = (permissions.IsAuthenticated, IsCustomer)

    def get_queryset(self):
        queryset = Alert.objects.filter(customer=self.request.user.profile.customer)
        return self.filter_queryset_by_timestamp(queryset)




@extend_schema_view(
    get=extend_schema(
        description="Retrieve detailed information of a specific alert.",
        responses={200: AlertSerializer},
    ),
    patch=extend_schema(
        description="Update the closure_code of an alert. Must provide a valid closure_code.",
        request=inline_serializer(
            name="AlertClosureCodeSerializer", fields={"closure_code": CharField()},
        ),
        responses={
            200: OpenApiResponse(description="Closure code updated successfully."),
            400: OpenApiResponse(description="Invalid closure code."),
        },
    ),
    post=extend_schema(
        description="Create and attach a MitigationStrategy to the alert.",
        request=MitigationStrategySerializer,
        responses={
            201: OpenApiResponse(description="Mitigation strategy created and linked to alert."),
            400: OpenApiResponse(description="Invalid or missing mitigation strategy data."),
        },
    ),
)
class AlertDetailView(RetrieveUpdateAPIView):
    """Analysis of the details of the alert object. Patch for setting closure_code and Post for assigning mitigation_strategy."""
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    permission_classes = (IsAuthenticatedWithMFA, IsAnalyst)
    lookup_field = 'pk'
    allowed_methods = ['GET', 'PATCH', 'POST']

    def post(self, request, *args, **kwargs):
        """
        Create MitigationStrategy and attach it to the alert.
        """
        alert = self.get_object()

        mitigation_data = request.data.get('description')
        if not mitigation_data:
            return Response({'detail': 'Mitigation strategy description is required.'},
                            status=status.HTTP_400_BAD_REQUEST)

        mitigation_serializer = MitigationStrategySerializer(data={"description":mitigation_data})
        pre_existing_strategy = MitigationStrategy.objects.filter(description=mitigation_data).first()
        if not mitigation_serializer.is_valid():
            return Response(mitigation_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        elif not pre_existing_strategy:
            mitigation_strategy = mitigation_serializer.save()
            alert.mitigation_strategy = mitigation_strategy
        elif pre_existing_strategy:

            alert.mitigation_strategy = pre_existing_strategy
        alert.save()
        return Response({'detail': 'Mitigation strategy created and linked to alert.'},
                        status=status.HTTP_201_CREATED)


    def patch(self, request, *args, **kwargs):
        """
        Update closure_code for alert.
        """
        closure_code = request.data.get('closure_code')
        if closure_code not in dict(Alert.CLOSURE_CODE_CHOICES).keys():
            return Response({'detail': 'Invalid closure code.'}, status=status.HTTP_400_BAD_REQUEST)

        alert = self.get_object()
        alert.closure_code = closure_code
        alert.status = 'validated'
        alert.validator = request.user
        alert.validated_at = now()
        alert.save()

        return Response({'detail': 'Closure code updated successfully.'}, status=status.HTTP_200_OK)


class MitigationStrategyListView(ListAPIView):
    """List of MitigationStrategy objects for Analysts."""
    queryset = MitigationStrategy.objects.all()
    serializer_class = MitigationStrategySerializer
    permission_classes = (IsAuthenticatedWithMFA, IsAnalyst)


class NonMaliciousListView(ListAPIView):
    """List of non-malicious Alerts that customer can remediate by himself"""
    queryset = Alert.objects.filter(closure_code='TPNM')
    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated, IsCustomer]

    def get_queryset(self):
        """
        Filter by the alert of a specific customer.
        """
        customer = self.request.user.profile.customer  # Assuming user has a related customer.
        return self.queryset.filter(customer=customer)


@extend_schema_view(
    get=extend_schema(
        description="Retrieve detailed information of a specific non-malicious alert by customer.",
        responses={200: AlertSerializer},
    ),
    patch=extend_schema(
        description="Mark an alert as mitigated by providing a valid mitigation strategy.",
        request=AlertMitigationSelectSerializer,  # Specify request serializer explicitly
        responses={
            200: AlertSerializer,
            400: OpenApiResponse(description="Invalid mitigation strategy."),
        },
    ),
    put=extend_schema(
        description="Mark an alert as resolved by the customer.",
        request=None,
        responses={
            200: OpenApiResponse(description="Alert marked as resolved."),
        },
    ),
)
class NonMaliciousUpdateResolveView(RetrieveUpdateAPIView):
    """
    View to handle non-malicious alerts. Customers can mark alerts as mitigated or resolved.
    """
    permission_classes = [permissions.IsAuthenticated, IsCustomer]

    def get_queryset(self):
        """
        Filter by the alert of a specific customer.
        """
        customer = self.request.user.profile.customer
        return Alert.objects.filter(Q(customer=customer) & Q(closure_code='TPNM'))

    def get_serializer_class(self):
        """
        Return serializer class based on the HTTP method.
        """
        if self.request.method == 'PATCH':
            return AlertMitigationSelectSerializer
        return AlertSerializer

    def patch(self, request, *args, **kwargs):
        """
        Endpoint to mark an alert as mitigated.
        This allows the customer to select a mitigation strategy.
        """
        alert = self.get_object()
        mitigation = request.data.get('mitigation')

        if mitigation and mitigation not in dict(Alert.MITIGATION_CHOICES):
            return Response({"detail": "Invalid mitigation strategy."}, status=status.HTTP_400_BAD_REQUEST)

        # Update the alert with the mitigation strategy and resolve the alert
        alert.mitigation = mitigation
        alert.save()

        return Response(AlertSerializer(alert).data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        """
        Customer can mark alert as resolved.
        """
        alert = self.get_object()
        alert.status = 'resolved'
        alert.resolver = request.user
        alert.resolved_at = now()
        alert.save()

        return Response({'detail': 'Alert marked as resolved.'}, status=status.HTTP_200_OK)


class CompanyEndpointsView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsCustomer]
    serializer_class = EndpointCustSerializer

    def get_queryset(self):
        customer = self.request.user.profile.customer
        return Endpoint.objects.filter(customer=customer)


class AnalystCompanyEndpointsView(ListAPIView):
    permission_classes = [IsAuthenticatedWithMFA, IsAnalyst]
    serializer_class = EndpointSerializer

    def get_queryset(self):
        company_name = self.kwargs.get("company_name")
        return Endpoint.objects.filter(customer__company_name=company_name)

@extend_schema(
    summary="Retrieve or deactivate an Endpoint",
    methods=["GET", "PATCH"],
    request=None,  # Порожнє тіло для PATCH
    responses={
        200: EndpointSerializer,
    },
)
class EndpointDetailView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticatedWithMFA, IsAnalyst]
    serializer_class = EndpointSerializer
    queryset = Endpoint.objects.all()
    allowed_methods = ['GET', 'PATCH']

    def update(self, request, *args, **kwargs):
        endpoint = self.get_object()

        endpoint.is_active = False
        endpoint.save()

        return super().update(request, *args, **kwargs)


@extend_schema_view(
    get=extend_schema(
        summary="Get statistics for customer endpoints",
        description="Returns the statistics of active and inactive endpoints for a given customer based on company name.",
        responses={
            200: inline_serializer(
                name='CustomerEndpointStatsResponse',
                fields={
                    'total_endpoints': serializers.IntegerField(),
                    'active_endpoints': serializers.IntegerField(),
                    'inactive_endpoints': serializers.IntegerField()
                }
            ),
            404: inline_serializer(
                name='NotFoundResponse',
                fields={'detail': serializers.CharField()}
            )
        }
    )
)
class CustomerEndpointDashboardView(APIView):
    serializer_class = EndpointSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if is_analyst(self.request):
            company_name = self.kwargs['company_name']
            try:
                customer = Customer.objects.get(company_name=company_name)
            except Customer.DoesNotExist:
                raise NotFound(detail="Customer not found.")
        else:
            customer = self.request.user.profile.customer

        return Endpoint.objects.filter(customer=customer)

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        active_count = queryset.filter(is_active=True).count()
        inactive_count = queryset.filter(is_active=False).count()

        response_data = {
            'total_endpoints': queryset.count(),
            'active_endpoints': active_count,
            'inactive_endpoints': inactive_count
        }
        return Response(response_data)


@extend_schema_view(
    get=extend_schema(
        summary="Get alert statistics for a customer",
        description=(
                "Retrieve detailed alert statistics for a specified customer within a given time range. "
                "The statistics include:\n"
                "- The number of alerts for each severity level (low, medium, high).\n"
                "- Daily event counts within the specified time range.\n"
                "- The number of alerts for each source.\n"
                "- The number of alerts for each status (open, validated, resolved)."
        ),
        parameters=[OpenApiParameter(
            name="after",
            description=(
                    "The start timestamp for filtering alerts. "
                    "Must be in ISO 8601 format (e.g., '2024-12-01T00:00:00Z'). "
                    "Ensure this value is earlier than the 'before' timestamp."
            ),
            required=False,
            type=OpenApiTypes.DATETIME,
        ),
            OpenApiParameter(
                name="before",
                description=(
                        "The end timestamp for filtering alerts. "
                        "Must be in ISO 8601 format (e.g., '2024-12-10T23:59:59Z'). "
                        "Ensure this value is later than the 'after' timestamp."
                ),
                required=False,
                type=OpenApiTypes.DATETIME,
            )
        ],
        responses={
            200: inline_serializer(
                name='CustomerAlertStatsResponse',
                fields={
                    'severity_stats': serializers.ListField(
                        child=inline_serializer(
                            name='SeverityStats',
                            fields={
                                'severity': serializers.CharField(
                                    help_text="Severity level (e.g., 'low', 'medium', 'high')."),
                                'count': serializers.IntegerField(
                                    help_text="Number of alerts with this severity level."),
                            }
                        )
                    ),
                    'event_counts': serializers.ListField(
                        child=inline_serializer(
                            name='EventCounts',
                            fields={
                                'date': serializers.CharField(help_text="The date (YYYY-MM-DD)."),
                                'count': serializers.IntegerField(help_text="Number of events on that date."),
                            }
                        )
                    ),
                    'source_stats': serializers.ListField(
                        child=inline_serializer(
                            name='SourceStats',
                            fields={
                                'source': serializers.CharField(help_text="The name of the source."),
                                'count': serializers.IntegerField(help_text="Number of alerts from this source."),
                            }
                        )
                    ),
                    'status_stats': serializers.ListField(
                        child=inline_serializer(
                            name='StatusStats',
                            fields={
                                'status': serializers.CharField(
                                    help_text="The alert status (e.g., 'open', 'validated', 'resolved')."),
                                'count': serializers.IntegerField(help_text="Number of alerts with this status."),
                            }
                        )
                    ),
                }
            ),
            404: inline_serializer(
                name='NotFoundResponse',
                fields={'detail': serializers.CharField(help_text="Error message indicating customer not found.")}
            )
        }
    )
)
class CustomerAlertDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self, after, before):
        if is_analyst(self.request):
            company_name = self.kwargs['company_name']
            try:
                customer = Customer.objects.get(company_name=company_name)
            except Customer.DoesNotExist:
                raise NotFound(detail="Customer not found.")
        else:
            customer = self.request.user.profile.customer

        alerts = Alert.objects.filter(
            customer=customer,
            timestamp__gte=after,
            timestamp__lte=before
        )
        return alerts

    def get(self, request, *args, **kwargs):
        after = request.query_params.get('after', (now() - timedelta(days=7)).isoformat())
        before = request.query_params.get('before', now().isoformat())

        # Convert 'after' and 'before' to datetime
        try:
            after = datetime.fromisoformat(after)
            before = datetime.fromisoformat(before)
        except ValueError:
            return Response({"detail": "Invalid datetime format."}, status=400)

        # Get the queryset for alerts in the given time range
        alerts = self.get_queryset(after, before)

        # Severity statistics
        severity_stats = (
            alerts.values('severity')
            .annotate(count=Count('severity'))
            .order_by('severity')
        )

        # Event counts by day
        event_counts = (
            alerts.annotate(day=TruncDate('timestamp'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )

        # Source statistics
        source_stats = (
            alerts.values('source__name')
            .annotate(count=Count('source'))
            .order_by('source__name')
        )

        # Status statistics
        status_stats = (
            alerts.values('status')
            .annotate(count=Count('status'))
            .order_by('status')
        )

        # Prepare data for charts.js
        severity_data = [{'severity': item['severity'], 'count': item['count']} for item in severity_stats]
        event_data = [{'date': item['day'].strftime('%Y-%m-%d'), 'count': item['count']} for item in event_counts]
        source_data = [{'source': item['source__name'], 'count': item['count']} for item in source_stats]
        status_data = [{'status': item['status'], 'count': item['count']} for item in status_stats]

        # Prepare final response
        response_data = {
            'severity_stats': severity_data,
            'event_counts': event_data,
            'source_stats': source_data,
            'status_stats': status_data
        }

        return Response(response_data)


@extend_schema(
    summary="Generate PDF Report",
    description=(
        "Generates a PDF report for a given customer within a specified time range. "
        "The report includes alert summaries, event counts, alert statuses, sources, "
        "and endpoint status information."
    ),
    parameters=[
        OpenApiParameter(
            name="company_name",
            description="The name of the customer's company.",
            required=False,
            type=str,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name="after",
            description="Start date (ISO 8601 format, e.g., '2024-12-01T00:00:00') for fetching report data.",
            required=False,
            type=str,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name="before",
            description="End date (ISO 8601 format, e.g., '2024-12-07T00:00:00') for fetching report data.",
            required=False,
            type=str,
            location=OpenApiParameter.QUERY,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=None,
            description="A downloadable PDF file containing the generated report.",
        ),
        400: OpenApiResponse(
            response=Response,
            description="Invalid date format or request parameters.",
        ),
        404: OpenApiResponse(
            response=Response,
            description="Customer not found.",
        ),
    },
)
class PDFReportView(APIView):
    def get(self, request, *args, **kwargs):
        if is_analyst(request)  :
            company_name = kwargs.get('company_name')
            try:
                customer = Customer.objects.get(company_name=company_name)
            except Customer.DoesNotExist:
                raise NotFound(detail="Customer not found.")
        else:
            customer = request.user.profile.customer
            company_name = customer.company_name

        after = request.query_params.get('after', (now() - timedelta(days=7)).isoformat())
        before = request.query_params.get('before', now().isoformat())

        # Convert timestamps to datetime objects
        try:
            after_date = datetime.fromisoformat(after)
            before_date = datetime.fromisoformat(before)
        except ValueError:
            return Response({"error": "Invalid date format. Use ISO 8601 format (e.g., 2024-12-01T00:00:00)."},
                            status=400)

        # Fetch data for alerts and endpoints
        alerts = Alert.objects.filter(customer=customer, timestamp__gte=after_date, timestamp__lte=before_date)
        endpoints = Endpoint.objects.filter(customer=customer)

        table_style = TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                  ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                  ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                  ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                  ('BOTTOMPADDING', (0, 0), (-1, 0), 12)])

        # Prepare data for the report (same as in CustomerAlertDashboardView)
        severity_stats = alerts.values('severity').annotate(count=Count('id'))
        status_stats = alerts.values('status').annotate(count=Count('id'))
        sources = alerts.values('source__name').annotate(count=Count('id'))

        # Event counts by day
        event_counts = (
            alerts.annotate(day=TruncDate('timestamp'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )

        # Prepare data for charts.js (this can be adapted to reportlab charts)
        event_data = [{'date': item['day'].strftime('%Y-%m-%d'), 'count': item['count']} for item in event_counts]
        severity_data = [{'severity': item['severity'], 'count': item['count']} for item in severity_stats]
        status_data = [{'status': item['status'], 'count': item['count']} for item in status_stats]
        source_data = [{'source': item['source__name'], 'count': item['count']} for item in sources]
        severity_order_fixer = severity_data.pop(1)
        severity_data.append(severity_order_fixer)

        # Generate PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, onFirstPage=self.add_page_number,
                                onLaterPages=self.add_page_number)
        elements = []
        styles = getSampleStyleSheet()

        # Title
        elements.append(Paragraph(f"Report for {customer.company_name}", styles['Title']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Data provided in this document is gathered "
                                  f"between {after_date.strftime("%Y-%m-%d")} and "
                                  f"{before_date.strftime("%Y-%m-%d")}",
                                  styles['Normal']))

        # --- Block 1: Alerts Summary (Table and Chart) ---
        elements.append(Paragraph("Alerts Summary", styles['Heading2']))
        alerts_table_data = [["Severity", "Count"]] + [[stat['severity'], stat['count']] for stat in severity_stats]
        alerts_table = Table(alerts_table_data, hAlign='LEFT')
        alerts_table.setStyle(table_style)
        elements.append(alerts_table)
        elements.append(Spacer(1, 12))

        # Severity Bar Chart
        drawing = Drawing(370, 180)
        chart = VerticalBarChart()
        chart.x = 50
        chart.y = 50
        chart.width = 300
        chart.height = 125
        chart.data = [[item['count'] for item in severity_data]]
        chart.categoryAxis.categoryNames = [item['severity'] for item in severity_data]
        chart.valueAxis.valueMin = 0
        counter = 0
        color_palette = [colors.coral, colors.yellow, colors.aquamarine]
        max_val = len(chart.bars)
        for i in range(0, max_val):
            chart.bars[i].fillColor = color_palette[counter % 7]
            counter += 1
        drawing.add(chart)
        elements.append(drawing)
        elements.append(Spacer(1, 24))

        # --- Block 2: Event Counts (Table and Chart) ---
        elements.append(Paragraph("Event Counts by Date", styles['Heading2']))
        event_table_data = [["Date", "Event Count"]] + [[item['date'], item['count']] for item in event_data]
        event_table = Table(event_table_data, hAlign='LEFT')
        event_table.setStyle(table_style)
        elements.append(event_table)
        elements.append(Spacer(1, 12))

        # Event Counts Line Chart
        drawing = Drawing(370, 180)
        chart = VerticalBarChart()
        chart.x = 50
        chart.y = 50
        chart.width = 300
        chart.height = 125
        chart.data = [[item['count'] for item in event_data]]
        chart.categoryAxis.categoryNames = [item['date'] for item in event_data]
        counter = 0
        color_palette = [colors.cyan, colors.aliceblue, colors.aqua, colors.aquamarine, colors.azure, colors.beige]
        max_val = len(chart.bars)
        for i in range(0, max_val):
            chart.bars[i].fillColor = color_palette[counter % 7]
            counter += 1
        drawing.add(chart)
        elements.append(drawing)
        elements.append(Spacer(1, 24))

        # --- Block 3: Alert Status (Table and Chart) ---
        elements.append(Paragraph("Alert Status Distribution", styles['Heading2']))
        status_table_data = [["Status", "Count"]] + [[item['status'], item['count']] for item in status_data]
        status_table = Table(status_table_data, hAlign='LEFT')
        status_table.setStyle(table_style)
        elements.append(status_table)
        elements.append(Spacer(1, 12))

        # Alert Status Pie Chart
        drawing = Drawing(370, 180)
        pie = Pie()
        pie.x = 50
        pie.y = 50
        pie.width = 180
        pie.height = 120
        pie.data = [item['count'] for item in status_data]
        pie.labels = [item['status'] for item in status_data]
        pie.slices[0].fillColor = colors.red
        pie.slices[1].fillColor = colors.yellow
        pie.slices[2].fillColor = colors.blue
        drawing.add(pie)
        elements.append(drawing)
        elements.append(Spacer(1, 24))

        # --- Block 4: Sources (Table and Chart) ---
        elements.append(Paragraph("Alert Sources", styles['Heading2']))
        sources_table_data = [["Source", "Count"]] + [[item['source__name'], item['count']] for item in sources]
        sources_table = Table(sources_table_data, hAlign='LEFT')
        sources_table.setStyle(table_style)
        elements.append(sources_table)
        elements.append(Spacer(1, 12))

        # Sources Bar Chart
        drawing = Drawing(370, 180)
        chart = VerticalBarChart()
        chart.x = 50
        chart.y = 50
        chart.width = 300
        chart.height = 125
        chart.data = [[item['count'] for item in source_data]]
        chart.categoryAxis.categoryNames = [item['source'] for item in source_data]
        chart.bars[0].fillColor = colors.limegreen
        drawing.add(chart)
        elements.append(drawing)
        elements.append(PageBreak())

        # --- Block 5: Endpoint Status Table ---
        elements.append(Paragraph("Endpoint Status", styles['Heading2']))
        endpoint_status_data = [["Endpoint", "Is Active"]] + [[endpoint.name, endpoint.is_active] for endpoint in
                                                              endpoints]
        endpoint_status_table = Table(endpoint_status_data, hAlign='LEFT')
        endpoint_status_table.setStyle(table_style)
        elements.append(endpoint_status_table)

        # Generate PDF
        doc.build(elements)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = (f'attachment; filename="{company_name}_report_'
                                           f'{after_date.strftime("%Y%m%d")}-{before_date.strftime("%Y%m%d")}.pdf"')
        return response

    @staticmethod
    def add_page_number(canvas, doc):
        page_number = f"Page {doc.page}"
        canvas.setFont('Helvetica', 10)
        canvas.setFillColor(colors.black)
        canvas.drawString(500, 20, page_number)
