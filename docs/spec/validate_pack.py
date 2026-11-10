from pathlib import Path
import json, re, sys
root=Path(__file__).resolve().parent
errors=[]; checks=[]
def require(ok,message):
    if not ok: errors.append(message)
    else: checks.append(message)
tasks=json.loads((root/'delivery/tasks.json').read_text())['tasks']
milestones=json.loads((root/'delivery/milestones.json').read_text())['milestones']
def graph(items,label):
    lookup={x['id']:x for x in items}
    require(len(lookup)==len(items),label+' unique IDs')
    seen=set(); active=set()
    def visit(k):
        if k not in lookup: errors.append(label+' missing dependency '+k); return
        if k in active: errors.append(label+' cycle at '+k); return
        if k in seen:return
        active.add(k)
        for d in lookup[k]['depends_on']:visit(d)
        active.remove(k); seen.add(k)
    for k in lookup:visit(k)
    require(len(seen)==len(items),label+' traversal complete')
graph(tasks,'tasks'); graph(milestones,'milestones')
require(len(tasks)==60,'60 tasks present'); require(len(milestones)==15,'15 milestones present')
for t in tasks:
    require((root/t['spec']).is_file(),t['id']+' specification exists')
    require(t['status']=='planned',t['id']+' correctly remains planned')
for m in milestones:
    require((root/'prompts'/f"{m['id']}_execution.md").is_file(),m['id']+' prompt exists')
    require(all(t in {x['id'] for x in tasks} for t in m['task_ids']),m['id']+' task references resolve')
scenarios=json.loads((root/'delivery/acceptance_scenarios.json').read_text())
require(len(scenarios)==24,'24 acceptance scenarios present')
requirements=(root/'03_master_requirements.md').read_text()
for s in scenarios:
    require(s['requirement'] in requirements,s['id']+' requirement resolves')
    require(s['status']=='not_run',s['id']+' correctly remains not_run')
for p in root.rglob('*.md'):
    for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
        if '://' in target or target.startswith('#'):continue
        require((p.parent/target.split('#')[0]).exists(),str(p.relative_to(root))+' link '+target)
api=json.loads((root/'contracts/openapi.json').read_text())
require(api['openapi']=='3.1.0','OpenAPI version')
ops=[]
for path,methods in api['paths'].items():
    for method,op in methods.items():
        ops.append(op['operationId'])
        require('responses' in op,path+' responses')
        for name in re.findall(r'\{(.*?)\}',path):
            require(any(p['name']==name and p['in']=='path' and p['required'] for p in op['parameters']),path+' path parameter '+name)
require(len(set(ops))==len(ops),'Unique operation IDs')
def refs(x):
    if isinstance(x,dict):
        if '$ref' in x:
            target=x['$ref']; require(target.startswith('#/components/schemas/') and target.split('/')[-1] in api['components']['schemas'],'Resolve '+target)
        for v in x.values():refs(v)
    elif isinstance(x,list):
        for v in x:refs(v)
refs(api)
try:
    import jsonschema
    for name in ['policy','webhook','task']:
        schema=json.loads((root/f'contracts/{name}.schema.json').read_text())
        jsonschema.Draft202012Validator.check_schema(schema)
        data=tasks if name=='task' else [json.loads((root/f'contracts/{name}.example.json').read_text())]
        for x in data:jsonschema.validate(x,schema)
    checks.append('JSON Schema definitions and examples/tasks validated')
except ImportError:errors.append('jsonschema dependency unavailable: schema validation not performed')
except Exception as e:errors.append('JSON Schema: '+str(e))
report={'status':'passed' if not errors else 'failed','scope':'Documentation/package structural validation only; application acceptance not run','checks_passed':len(checks),'errors':errors,'tasks':len(tasks),'milestones':len(milestones),'acceptance_scenarios':len(scenarios),'api_operations':len(ops)}
(root/'VALIDATION_REPORT.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2)); sys.exit(bool(errors))
