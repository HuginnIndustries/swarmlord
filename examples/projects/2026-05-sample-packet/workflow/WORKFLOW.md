---
runner_profile: manual
phase: discovery
hooks:
  after_create: null
  before_run: null
  after_run: null
  before_remove: null
  timeout_ms: 60000
agent:
  max_turns: 5
  completion_signal: "<promise>COMPLETE</promise>"
gates:
  promote_to_spec_ready:
    - kind: file_section_filled
      path: spec/discovery.md
      section: "## Recommended Direction"
    - kind: yaml_field_empty
      path: workflow/status.yaml
      field: open_questions
  promote_to_build_ready:
    - kind: file_section_filled
      path: spec/build-spec.md
      section: "## Outcome"
    - kind: file_section_filled
      path: spec/build-spec.md
      section: "## Acceptance Criteria"
    - kind: file_section_filled
      path: spec/build-spec.md
      section: "## Test Plan"
    - kind: yaml_field_empty
      path: workflow/status.yaml
      field: open_questions
    - kind: extract_md_resolved
  promote_to_extracted:
    - kind: extract_md_resolved
---

You are continuing work on packet `{{ packet.slug }}`.

Current stage: {{ packet.stage.value }}.
Current phase: {{ packet.current_phase.value }}.

{% if attempt %}
This is retry attempt {{ attempt }}. Resume from existing files without redoing finished sections.
{% endif %}

Open questions:
{% for q in packet.open_questions %}
- {{ q }}
{% endfor %}

{% if graph_report_path %}
A knowledge graph for this packet exists at `{{ graph_report_path }}`.
Read GRAPH_REPORT.md before grepping raw files.
{% endif %}

Next actions:
{% for a in packet.next_actions %}
- {{ a }}
{% endfor %}

Update the relevant spec file(s) and `workflow/status.yaml` when done.
Append a `THREAD_LOG.md` entry. Emit `<promise>COMPLETE</promise>` to finish.
