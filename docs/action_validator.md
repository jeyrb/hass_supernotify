# Action Validator

Try out the calls to the supernotifier action with this interactive validator.

<!-- Add to your MkDocs template or as a custom HTML block -->
<div id="yaml-editor" style="height: 400px; border: 1px solid #ccc;"></div>
<div id="validation-output"></div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/ajv/8.17.1/ajv2020.bundle.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs/loader.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/js-yaml/4.1.0/js-yaml.min.js" type="module"></script>

<script>
require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs' }});
require(['vs/editor/editor.main'], function() {
    const Ajv = window.ajv2020;
    const jsyaml = require('js-yaml');
    const editor = monaco.editor.create(document.getElementById('yaml-editor'), {
        value: `# Your example YAML here
data:
    priority: medium
    apply-scenarios:
        - routine
`,
        language: 'yaml',
        theme: 'vs-dark',
        minimap: { enabled: false }
    });

    // Load JSON schema from URL
    fetch('http://127.0.0.1:8000/hass_supernotify/js/schema.json')
        .then(response => response.json())
        .then(schema => {
            const ajv = new Ajv();
            const validate = ajv.compile(schema);

            function validateYAML() {
                try {
                    const yamlContent = editor.getValue();
                    const parsed = jsyaml.load(yamlContent);
                    const valid = validate(parsed);

                    const output = document.getElementById('validation-output');
                    if (valid) {
                        output.innerHTML = '<span style="color: green;">✓ Valid YAML</span>';
                    } else {
                        output.innerHTML = '<span style="color: red;">✗ Validation errors: ' +
                            validate.errors.map(err => err.message).join(', ') + '</span>';
                    }
                } catch (e) {
                    document.getElementById('validation-output').innerHTML =
                        '<span style="color: red;">✗ YAML Parse Error: ' + e.message + '</span>';
                }
            }

            editor.onDidChangeModelContent(validateYAML);
            validateYAML(); // Initial validation
        });

});
</script>
