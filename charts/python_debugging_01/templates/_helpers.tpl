{{/* Common metadata labels. Resource/service names are kept STABLE
     (crawler / wikipedia / sidecar) so in-cluster DNS is predictable —
     the sidecar's UPSTREAM and the validator's entry both rely on it. */}}
{{- define "pd01.labels" -}}
app.kubernetes.io/part-of: python-debugging-01
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}
