{{- define "sre-lab.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "sre-lab.labels" -}}
{{ include "sre-lab.selectorLabels" . }}
app.kubernetes.io/version: {{ include "sre-lab.imageTag" . | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{- define "sre-lab.imageTag" -}}
{{ .Values.image.tag | default .Chart.AppVersion }}
{{- end }}
