"""Isolamento por empresa (multi-tenant com esquema compartilhado).

Toda tabela de dados de negócio tem `organization`. Estes mixins garantem que:
  1. a API só enxerga registros da empresa do usuário (queryset filtrado);
  2. registros novos nascem na empresa do usuário;
  3. campos de relação (veículo, motorista...) só aceitam objetos da mesma empresa,
     para ninguém referenciar dados de outra empresa pelo id.
"""


class TenantQuerysetMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        if getattr(self, "swagger_fake_view", False):  # geração do schema OpenAPI
            return queryset.none()
        return queryset.filter(organization_id=self.request.user.organization_id)

    def get_create_kwargs(self):
        base = getattr(super(), "get_create_kwargs", dict)()
        return {**base, "organization_id": self.request.user.organization_id}


class TenantSerializerMixin:
    tenant_related = {}  # nome do campo -> Model (ex.: {"vehicle": Vehicle})

    def _org_id(self):
        request = self.context.get("request")
        return getattr(getattr(request, "user", None), "organization_id", None)

    def get_fields(self):
        fields = super().get_fields()
        for name, model in self.tenant_related.items():
            if name in fields:
                fields[name].queryset = model.objects.filter(organization_id=self._org_id())
        return fields
