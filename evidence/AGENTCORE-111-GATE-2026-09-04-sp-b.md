# Case trace — `OBS-SPB-CBF40` (tenant `sp-b`)

| metric | value |
|---|---|
| agent_spans | 1 |
| gateway_requests | 38 |
| lambda_calls | 8 |
| lambda_calls_joined_to_evidence | 7 |
| masked_before_model_all | True |
| model_invocations | 6 |
| model_invocations_joined_to_spans | 6 |
| model_invocations_tagged_tenant | 6 |
| model_spans | 12 |
| sessions | ['aegis-sp-b-0620f5e6a1db4658a94b96df0807337c'] |
| single_tenant | True |
| tenants_seen | ['sp-b'] |
| tool_spans | 14 |
| worm_records | 1 |

| time (UTC) | source | kind | what | join keys |
|---|---|---|---|---|
| 19:19:53.174 | lambda | call | ingest_application -> ingested=True | trace_id=6a9b19d8585891c922 request_id=e682ec18-0d70-4990 tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:19:53.756 | runtime-span | runtime-invoke | AgentCore.Runtime.Invoke | trace_id=6a9b19d91e658b3079 span_id=fa7e8f563d4aa1e3 session_id=aegis-sp-b-0620f5e |
| 19:19:55.000 | bedrock-model-log | model-invocation | Converse us.anthropic.claude-sonnet-4-5-20250929-v1:0 in=3666 out=164 masked_before_model=True | request_id=1678a493-67b3-413c session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:19:55.004 | runtime-span | runtime-http | POST /invocations | trace_id=6a9b19d91e658b3079 span_id=548125ae12bcc6fa session_id=aegis-sp-b-0620f5e |
| 19:19:55.097 | runtime-span | span | SSM.GetParameter | trace_id=6a9b19d91e658b3079 span_id=b05e854cf9261299 session_id=aegis-sp-b-0620f5e |
| 19:19:55.144 | runtime-span | span | SSM.GetParameter | trace_id=6a9b19d91e658b3079 span_id=c3c4234386431e0e session_id=aegis-sp-b-0620f5e |
| 19:19:55.207 | runtime-span | span | DynamoDB.GetItem | trace_id=6a9b19d91e658b3079 span_id=edaa499d6319ccb7 session_id=aegis-sp-b-0620f5e |
| 19:19:55.259 | runtime-span | span | DynamoDB.GetItem | trace_id=6a9b19d91e658b3079 span_id=f7ae02180dd9c6be session_id=aegis-sp-b-0620f5e |
| 19:19:55.358 | runtime-span | span | mcp.session | trace_id=6a9b19d91e658b3079 span_id=47bebf3f101f7759 session_id=aegis-sp-b-0620f5e |
| 19:19:55.508 | runtime-span | mcp-list | mcp tools/list | trace_id=6a9b19d91e658b3079 span_id=e8c253bf94aaef6a session_id=aegis-sp-b-0620f5e |
| 19:19:55.714 | runtime-span | lambda-segment | fa-mt-tenant-interceptor/LambdaService | trace_id=6a9b19d91e658b3079 span_id=3e85b51d0ac21808 |
| 19:19:55.720 | runtime-span | lambda-segment | fa-mt-tenant-interceptor/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=95f2be752b82aa62 |
| 19:19:55.720 | runtime-span | lambda-segment | Overhead/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=2a5ce5122d2fd104 |
| 19:19:55.723 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549595723,"body":{"isError":false,"log" | session_id=aegis-sp-b-0620f5e trace_id=6a9b19d91e658b3079 |
| 19:19:55.727 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549595727,"body":{"isError":false,"log" | trace_id=6a9b19d91e658b3079 |
| 19:19:55.825 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549595825,"body":{"isError":false,"resp | trace_id=6a9b19d91e658b3079 |
| 19:19:55.833 | runtime-span | agent | invoke_agent Strands Agents model=us.anthropic.claude-sonnet-4-5-20250929-v1:0 in=28919 out=1766 | trace_id=6a9b19d91e658b3079 span_id=3c64e47a8deaebdf session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:19:55.834 | runtime-span | cycle | execute_event_loop_cycle | trace_id=6a9b19d91e658b3079 span_id=f9f9ed786ce78aff session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:19:55.835 | runtime-span | model | chat model=us.anthropic.claude-sonnet-4-5-20250929-v1:0 in=3666 out=164 | trace_id=6a9b19d91e658b3079 span_id=2e0d8fbe31f2d00f session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:19:55.852 | runtime-span | model | chat us.anthropic.claude-sonnet-4-5-20250929-v1:0 model=us.anthropic.claude-sonnet-4-5-20250929-v1:0 in=3666 out=164 | trace_id=6a9b19d91e658b3079 span_id=3c1aee8d02ab1e29 session_id=aegis-sp-b-0620f5e request_id=1678a493-67b3-413c |
| 19:19:55.853 | runtime-span | span | DynamoDB.UpdateItem | trace_id=6a9b19d91e658b3079 span_id=f6f1c47623c2c886 session_id=aegis-sp-b-0620f5e |
| 19:19:58.883 | runtime-span | span | DynamoDB.UpdateItem | trace_id=6a9b19d91e658b3079 span_id=f139e7f67c92d4f6 session_id=aegis-sp-b-0620f5e |
| 19:19:58.899 | runtime-span | span | CloudWatch.PutMetricData | trace_id=6a9b19d91e658b3079 span_id=39c07e60cd21c1d3 session_id=aegis-sp-b-0620f5e |
| 19:19:58.938 | runtime-span | tool | execute_tool intake-fafsa___intake_fafsa tool=intake-fafsa___intake_fafsa | trace_id=6a9b19d91e658b3079 span_id=3300828fd41734c8 session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:19:58.938 | runtime-span | tool | execute_tool mask-pii___mask_pii tool=mask-pii___mask_pii | trace_id=6a9b19d91e658b3079 span_id=602307935890f832 session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:19:58.939 | runtime-span | tool | mcp tools/call intake-fafsa___intake_fafsa tool=intake-fafsa___intake_fafsa | trace_id=6a9b19d91e658b3079 span_id=de4413d2e57e2bd6 session_id=aegis-sp-b-0620f5e |
| 19:19:58.940 | runtime-span | tool | mcp tools/call mask-pii___mask_pii tool=mask-pii___mask_pii | trace_id=6a9b19d91e658b3079 span_id=ee378988cff04c3c session_id=aegis-sp-b-0620f5e |
| 19:19:59.000 | bedrock-model-log | model-invocation | Converse us.anthropic.claude-sonnet-4-5-20250929-v1:0 in=4328 out=229 masked_before_model=True | request_id=0659ed82-ec9b-479a session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:19:59.032 | runtime-span | lambda-segment | fa-mt-tenant-interceptor/LambdaService | trace_id=6a9b19d91e658b3079 span_id=6b6e2c559f4486c2 |
| 19:19:59.038 | runtime-span | lambda-segment | fa-mt-tenant-interceptor/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=d34884442be0844d |
| 19:19:59.049 | runtime-span | lambda-segment | fa-mt-tenant-interceptor/LambdaService | trace_id=6a9b19d91e658b3079 span_id=08ff5bff525ad8ca |
| 19:19:59.055 | runtime-span | lambda-segment | fa-mt-tenant-interceptor/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=04e07c5499290dcb |
| 19:19:59.060 | runtime-span | lambda-segment | Overhead/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=440d3946ae469b35 |
| 19:19:59.063 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549599063,"body":{"isError":false,"log" | session_id=aegis-sp-b-0620f5e trace_id=6a9b19d91e658b3079 |
| 19:19:59.066 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549599066,"body":{"isError":false,"log" | trace_id=6a9b19d91e658b3079 |
| 19:19:59.086 | runtime-span | lambda-segment | Overhead/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=465b320aae8328df |
| 19:19:59.089 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549599089,"body":{"isError":false,"log" | session_id=aegis-sp-b-0620f5e trace_id=6a9b19d91e658b3079 |
| 19:19:59.093 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549599093,"body":{"isError":false,"log" | trace_id=6a9b19d91e658b3079 |
| 19:19:59.138 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549599138,"body":{"isError":false,"log" | trace_id=6a9b19d91e658b3079 |
| 19:19:59.158 | runtime-span | lambda-segment | fa-mt-intake-fafsa/LambdaService | trace_id=6a9b19d91e658b3079 span_id=7dde37870fc94640 |
| 19:19:59.165 | runtime-span | lambda-segment | fa-mt-intake-fafsa/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=9d019c9fbf308c15 |
| 19:19:59.169 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549599169,"body":{"isError":false,"log" | trace_id=6a9b19d91e658b3079 |
| 19:19:59.196 | runtime-span | lambda-segment | fa-mt-mask-pii/LambdaService | trace_id=6a9b19d91e658b3079 span_id=094730baef8504c0 |
| 19:19:59.201 | runtime-span | lambda-segment | fa-mt-mask-pii/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=fceaa7cde0639b99 |
| 19:19:59.279 | lambda | call | intake_fafsa -> ok | trace_id=6a9b19d91e658b3079 session_id=aegis-sp-b-0620f5e request_id=78b0e87f-b55e-45b9 tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:19:59.280 | runtime-span | lambda-segment | Overhead/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=fe6a245a7cd4fd8b |
| 19:19:59.284 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549599284,"body":{"isError":false,"log" | trace_id=6a9b19d91e658b3079 |
| 19:19:59.284 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549599284,"body":{"isError":false,"resp | trace_id=6a9b19d91e658b3079 |
| 19:19:59.656 | lambda | call | mask_pii -> deidentified=True | trace_id=6a9b19d91e658b3079 session_id=aegis-sp-b-0620f5e request_id=be7cd992-c8b1-47e6 tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:19:59.656 | runtime-span | lambda-segment | Overhead/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=636552854cc36d77 |
| 19:19:59.661 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549599661,"body":{"isError":false,"resp | trace_id=6a9b19d91e658b3079 |
| 19:19:59.662 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549599662,"body":{"isError":false,"log" | trace_id=6a9b19d91e658b3079 |
| 19:19:59.667 | runtime-span | cycle | execute_event_loop_cycle | trace_id=6a9b19d91e658b3079 span_id=0ba5222f110c2381 session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:19:59.668 | runtime-span | model | chat model=us.anthropic.claude-sonnet-4-5-20250929-v1:0 in=4328 out=229 | trace_id=6a9b19d91e658b3079 span_id=cde13dccb16a3143 session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:19:59.669 | runtime-span | span | DynamoDB.UpdateItem | trace_id=6a9b19d91e658b3079 span_id=b834b2bc0e1a6538 session_id=aegis-sp-b-0620f5e |
| 19:19:59.669 | runtime-span | model | chat us.anthropic.claude-sonnet-4-5-20250929-v1:0 model=us.anthropic.claude-sonnet-4-5-20250929-v1:0 in=4328 out=229 | trace_id=6a9b19d91e658b3079 span_id=0364ed123f036d6c session_id=aegis-sp-b-0620f5e request_id=0659ed82-ec9b-479a |
| 19:20:04.000 | bedrock-model-log | model-invocation | Converse us.anthropic.claude-sonnet-4-5-20250929-v1:0 in=4625 out=190 masked_before_model=True | request_id=6fabc42a-3de7-432c session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:20:04.061 | runtime-span | span | DynamoDB.UpdateItem | trace_id=6a9b19d91e658b3079 span_id=c733f353ed9ebc60 session_id=aegis-sp-b-0620f5e |
| 19:20:04.067 | runtime-span | span | CloudWatch.PutMetricData | trace_id=6a9b19d91e658b3079 span_id=cdddc3bd2ad90d9f session_id=aegis-sp-b-0620f5e |
| 19:20:04.078 | runtime-span | tool | execute_tool assess-aid___assess_aid tool=assess-aid___assess_aid | trace_id=6a9b19d91e658b3079 span_id=21c3d5c6bc7ff496 session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:20:04.079 | runtime-span | tool | mcp tools/call assess-aid___assess_aid tool=assess-aid___assess_aid | trace_id=6a9b19d91e658b3079 span_id=aead13d27694bac0 session_id=aegis-sp-b-0620f5e |
| 19:20:04.188 | runtime-span | lambda-segment | fa-mt-tenant-interceptor/LambdaService | trace_id=6a9b19d91e658b3079 span_id=43b86862558e29a6 |
| 19:20:04.194 | runtime-span | lambda-segment | fa-mt-tenant-interceptor/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=872ec8d3e8774af9 |
| 19:20:04.199 | runtime-span | lambda-segment | Overhead/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=9b53fe24fdc8a307 |
| 19:20:04.202 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549604202,"body":{"isError":false,"log" | session_id=aegis-sp-b-0620f5e trace_id=6a9b19d91e658b3079 |
| 19:20:04.208 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549604208,"body":{"isError":false,"log" | trace_id=6a9b19d91e658b3079 |
| 19:20:04.291 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549604291,"body":{"isError":false,"log" | trace_id=6a9b19d91e658b3079 |
| 19:20:04.316 | runtime-span | lambda-segment | fa-mt-assess-aid/LambdaService | trace_id=6a9b19d91e658b3079 span_id=58c1d3e9b654f333 |
| 19:20:04.321 | runtime-span | lambda-segment | fa-mt-assess-aid/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=4a2e7fe0f874f6a5 |
| 19:20:04.344 | lambda | call | assess_aid -> error | trace_id=6a9b19d91e658b3079 session_id=aegis-sp-b-0620f5e request_id=be6f6e00-2564-4c8f tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:20:04.352 | runtime-span | lambda-segment | Overhead/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=ab2af95778772c77 |
| 19:20:04.357 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549604357,"body":{"isError":false,"log" | trace_id=6a9b19d91e658b3079 |
| 19:20:04.357 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549604357,"body":{"isError":false,"resp | trace_id=6a9b19d91e658b3079 |
| 19:20:04.364 | runtime-span | cycle | execute_event_loop_cycle | trace_id=6a9b19d91e658b3079 span_id=27c23cd6235d4ab1 session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:20:04.365 | runtime-span | model | chat model=us.anthropic.claude-sonnet-4-5-20250929-v1:0 in=4625 out=190 | trace_id=6a9b19d91e658b3079 span_id=ae95ccc3869846bb session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:20:04.366 | runtime-span | span | DynamoDB.UpdateItem | trace_id=6a9b19d91e658b3079 span_id=a8c4d7c5459e9b3e session_id=aegis-sp-b-0620f5e |
| 19:20:04.366 | runtime-span | model | chat us.anthropic.claude-sonnet-4-5-20250929-v1:0 model=us.anthropic.claude-sonnet-4-5-20250929-v1:0 in=4625 out=190 | trace_id=6a9b19d91e658b3079 span_id=528103d7ce466d14 session_id=aegis-sp-b-0620f5e request_id=6fabc42a-3de7-432c |
| 19:20:07.000 | bedrock-model-log | model-invocation | Converse us.anthropic.claude-sonnet-4-5-20250929-v1:0 in=4883 out=416 masked_before_model=True | request_id=b7ea1555-ec89-427d session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:20:07.494 | runtime-span | span | DynamoDB.UpdateItem | trace_id=6a9b19d91e658b3079 span_id=b47b37008d2b1fe5 session_id=aegis-sp-b-0620f5e |
| 19:20:07.500 | runtime-span | span | CloudWatch.PutMetricData | trace_id=6a9b19d91e658b3079 span_id=0098efdfeac55794 session_id=aegis-sp-b-0620f5e |
| 19:20:07.510 | runtime-span | tool | execute_tool assess-aid___assess_aid tool=assess-aid___assess_aid | trace_id=6a9b19d91e658b3079 span_id=7be96f954e1a003c session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:20:07.511 | runtime-span | tool | mcp tools/call assess-aid___assess_aid tool=assess-aid___assess_aid | trace_id=6a9b19d91e658b3079 span_id=3bc0acfcabd80d14 session_id=aegis-sp-b-0620f5e |
| 19:20:07.599 | runtime-span | lambda-segment | fa-mt-tenant-interceptor/LambdaService | trace_id=6a9b19d91e658b3079 span_id=61693a267ec9612c |
| 19:20:07.603 | runtime-span | lambda-segment | fa-mt-tenant-interceptor/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=91e05a5e6d554c06 |
| 19:20:07.608 | runtime-span | lambda-segment | Overhead/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=0e4982da681041f1 |
| 19:20:07.610 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549607610,"body":{"isError":false,"log" | session_id=aegis-sp-b-0620f5e trace_id=6a9b19d91e658b3079 |
| 19:20:07.615 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549607615,"body":{"isError":false,"log" | trace_id=6a9b19d91e658b3079 |
| 19:20:07.696 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549607696,"body":{"isError":false,"log" | trace_id=6a9b19d91e658b3079 |
| 19:20:07.721 | runtime-span | lambda-segment | fa-mt-assess-aid/LambdaService | trace_id=6a9b19d91e658b3079 span_id=630842c72cc99aeb |
| 19:20:07.728 | lambda | call | assess_aid -> error | trace_id=6a9b19d91e658b3079 session_id=aegis-sp-b-0620f5e request_id=248b5032-dbb1-46d5 tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:20:07.728 | runtime-span | lambda-segment | fa-mt-assess-aid/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=d1f3b700ca6a757e |
| 19:20:07.728 | runtime-span | lambda-segment | Overhead/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=bc49197d8071c398 |
| 19:20:07.732 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549607732,"body":{"isError":false,"log" | trace_id=6a9b19d91e658b3079 |
| 19:20:07.732 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549607732,"body":{"isError":false,"resp | trace_id=6a9b19d91e658b3079 |
| 19:20:07.738 | runtime-span | cycle | execute_event_loop_cycle | trace_id=6a9b19d91e658b3079 span_id=10b559a5fc957288 session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:20:07.739 | runtime-span | model | chat model=us.anthropic.claude-sonnet-4-5-20250929-v1:0 in=4883 out=416 | trace_id=6a9b19d91e658b3079 span_id=f14046d906ad2811 session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:20:07.740 | runtime-span | model | chat us.anthropic.claude-sonnet-4-5-20250929-v1:0 model=us.anthropic.claude-sonnet-4-5-20250929-v1:0 in=4883 out=416 | trace_id=6a9b19d91e658b3079 span_id=5278bebe51d37628 session_id=aegis-sp-b-0620f5e request_id=b7ea1555-ec89-427d |
| 19:20:07.741 | runtime-span | span | DynamoDB.UpdateItem | trace_id=6a9b19d91e658b3079 span_id=207962fa546fb06e session_id=aegis-sp-b-0620f5e |
| 19:20:14.000 | bedrock-model-log | model-invocation | Converse us.anthropic.claude-sonnet-4-5-20250929-v1:0 in=5350 out=334 masked_before_model=True | request_id=77b03d6c-a2df-46fa session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:20:14.447 | runtime-span | span | DynamoDB.UpdateItem | trace_id=6a9b19d91e658b3079 span_id=dd048fca2d732104 session_id=aegis-sp-b-0620f5e |
| 19:20:14.454 | runtime-span | span | CloudWatch.PutMetricData | trace_id=6a9b19d91e658b3079 span_id=ea8327cf4a660f49 session_id=aegis-sp-b-0620f5e |
| 19:20:14.489 | runtime-span | tool | execute_tool fa-core___draft_award_notice tool=fa-core___draft_award_notice | trace_id=6a9b19d91e658b3079 span_id=68539fd1a5aad0c8 session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:20:14.490 | runtime-span | tool | mcp tools/call fa-core___draft_award_notice tool=fa-core___draft_award_notice | trace_id=6a9b19d91e658b3079 span_id=9800e9e770e64226 session_id=aegis-sp-b-0620f5e |
| 19:20:14.601 | runtime-span | lambda-segment | fa-mt-tenant-interceptor/LambdaService | trace_id=6a9b19d91e658b3079 span_id=194db592f12768d4 |
| 19:20:14.608 | runtime-span | lambda-segment | fa-mt-tenant-interceptor/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=a4234319306c02a6 |
| 19:20:14.636 | runtime-span | lambda-segment | Overhead/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=fa5548113689ee96 |
| 19:20:14.640 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549614640,"body":{"isError":false,"log" | session_id=aegis-sp-b-0620f5e trace_id=6a9b19d91e658b3079 |
| 19:20:14.643 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549614643,"body":{"isError":false,"log" | trace_id=6a9b19d91e658b3079 |
| 19:20:14.720 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549614720,"body":{"isError":false,"log" | trace_id=6a9b19d91e658b3079 |
| 19:20:14.744 | runtime-span | lambda-segment | fa-mt-core-tools/LambdaService | trace_id=6a9b19d91e658b3079 span_id=7d9200d3fc05d767 |
| 19:20:14.748 | runtime-span | lambda-segment | fa-mt-core-tools/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=44c322fc975e441c |
| 19:20:14.771 | lambda | call | aid_core -> error | trace_id=6a9b19d91e658b3079 session_id=aegis-sp-b-0620f5e request_id=c31ee2bf-79d7-4347 tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:20:14.772 | runtime-span | lambda-segment | Overhead/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=e7f7e741bf4fb9dc |
| 19:20:14.775 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549614775,"body":{"isError":false,"log" | trace_id=6a9b19d91e658b3079 |
| 19:20:14.775 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549614775,"body":{"isError":false,"resp | trace_id=6a9b19d91e658b3079 |
| 19:20:14.781 | runtime-span | cycle | execute_event_loop_cycle | trace_id=6a9b19d91e658b3079 span_id=0cf45d871efaee23 session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:20:14.782 | runtime-span | model | chat model=us.anthropic.claude-sonnet-4-5-20250929-v1:0 in=5350 out=334 | trace_id=6a9b19d91e658b3079 span_id=af4075027101f142 session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:20:14.783 | runtime-span | model | chat us.anthropic.claude-sonnet-4-5-20250929-v1:0 model=us.anthropic.claude-sonnet-4-5-20250929-v1:0 in=5350 out=334 | trace_id=6a9b19d91e658b3079 span_id=09b0bd90ef4630ba session_id=aegis-sp-b-0620f5e request_id=77b03d6c-a2df-46fa |
| 19:20:14.791 | runtime-span | span | SSM.GetParameter | trace_id=6a9b19d91e658b3079 span_id=f8655db1dd78674a session_id=aegis-sp-b-0620f5e |
| 19:20:14.834 | runtime-span | span | DynamoDB.UpdateItem | trace_id=6a9b19d91e658b3079 span_id=d7fe2af154463411 session_id=aegis-sp-b-0620f5e |
| 19:20:19.676 | runtime-span | span | DynamoDB.UpdateItem | trace_id=6a9b19d91e658b3079 span_id=8d5ca021d33b968d session_id=aegis-sp-b-0620f5e |
| 19:20:19.682 | runtime-span | span | CloudWatch.PutMetricData | trace_id=6a9b19d91e658b3079 span_id=e47d44aae68d3ba6 session_id=aegis-sp-b-0620f5e |
| 19:20:19.692 | runtime-span | tool | execute_tool write-audit___write_audit tool=write-audit___write_audit | trace_id=6a9b19d91e658b3079 span_id=b46d41fd19ec5f78 session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:20:19.693 | runtime-span | tool | execute_tool request-signoff___request_signoff tool=request-signoff___request_signoff | trace_id=6a9b19d91e658b3079 span_id=f488a23877b983f4 session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:20:19.693 | runtime-span | tool | mcp tools/call write-audit___write_audit tool=write-audit___write_audit | trace_id=6a9b19d91e658b3079 span_id=0190fbd89e3e5adc session_id=aegis-sp-b-0620f5e |
| 19:20:19.694 | runtime-span | tool | mcp tools/call request-signoff___request_signoff tool=request-signoff___request_signoff | trace_id=6a9b19d91e658b3079 span_id=dafb82d49fb14a28 session_id=aegis-sp-b-0620f5e |
| 19:20:19.793 | runtime-span | lambda-segment | fa-mt-tenant-interceptor/LambdaService | trace_id=6a9b19d91e658b3079 span_id=68d286053b3817c4 |
| 19:20:19.799 | runtime-span | lambda-segment | fa-mt-tenant-interceptor/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=fd237de2d3277739 |
| 19:20:19.804 | runtime-span | lambda-segment | Overhead/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=6024bb3c69d61da6 |
| 19:20:19.807 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549619807,"body":{"isError":false,"log" | session_id=aegis-sp-b-0620f5e trace_id=6a9b19d91e658b3079 |
| 19:20:19.808 | runtime-span | lambda-segment | fa-mt-tenant-interceptor/LambdaService | trace_id=6a9b19d91e658b3079 span_id=18c329208d690129 |
| 19:20:19.813 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549619813,"body":{"isError":false,"log" | trace_id=6a9b19d91e658b3079 |
| 19:20:19.815 | runtime-span | lambda-segment | fa-mt-tenant-interceptor/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=741ce92c4ea3f877 |
| 19:20:19.823 | runtime-span | lambda-segment | Overhead/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=dd15edd71e265e6f |
| 19:20:19.826 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549619826,"body":{"isError":false,"log" | session_id=aegis-sp-b-0620f5e trace_id=6a9b19d91e658b3079 |
| 19:20:19.831 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549619831,"body":{"isError":false,"log" | trace_id=6a9b19d91e658b3079 |
| 19:20:19.892 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549619892,"body":{"isError":false,"log" | trace_id=6a9b19d91e658b3079 |
| 19:20:19.905 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549619905,"body":{"isError":false,"log" | trace_id=6a9b19d91e658b3079 |
| 19:20:19.924 | runtime-span | lambda-segment | fa-mt-write-audit/LambdaService | trace_id=6a9b19d91e658b3079 span_id=221a88503ba4f247 |
| 19:20:19.928 | runtime-span | lambda-segment | fa-mt-write-audit/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=ae27b0bedadfe84b |
| 19:20:19.934 | runtime-span | lambda-segment | fa-mt-request-signoff/LambdaService | trace_id=6a9b19d91e658b3079 span_id=4a111ffae231e69c |
| 19:20:19.939 | runtime-span | lambda-segment | fa-mt-request-signoff/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=43915d0bc48ddbdd |
| 19:20:19.958 | lambda | call | request_signoff -> requested=False | trace_id=6a9b19d91e658b3079 session_id=aegis-sp-b-0620f5e request_id=51ab1feb-bf03-4175 tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:20:19.959 | runtime-span | lambda-segment | Overhead/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=57f74d928f3d8cb0 |
| 19:20:19.966 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549619966,"body":{"isError":false,"log" | trace_id=6a9b19d91e658b3079 |
| 19:20:19.966 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549619966,"body":{"isError":false,"resp | trace_id=6a9b19d91e658b3079 |
| 19:20:20.000 | bedrock-model-log | model-invocation | Converse us.anthropic.claude-sonnet-4-5-20250929-v1:0 in=6067 out=433 masked_before_model=True | request_id=df8723e3-1540-48d1 session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:20:20.000 | worm | evidence | INTENT benefits-determination seq=0 chain=a7b5ae14259e… | trace_id=6a9b19d91e658b3079 session_id=aegis-sp-b-0620f5e request_id=b56773dd-50c1-4bfd tenant=sp-b |
| 19:20:20.418 | lambda | call | write_audit -> stored=True | trace_id=6a9b19d91e658b3079 session_id=aegis-sp-b-0620f5e request_id=b56773dd-50c1-4bfd tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:20:20.419 | runtime-span | lambda-segment | Overhead/LambdaExecutionEnvironment | trace_id=6a9b19d91e658b3079 span_id=a17a67ad9401e589 |
| 19:20:20.424 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549620424,"body":{"isError":false,"log" | trace_id=6a9b19d91e658b3079 |
| 19:20:20.424 | gateway | request | {"resource_arn":"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-mt-aid-gw-jesedgqve1","event_timestamp":1788549620424,"body":{"isError":false,"resp | trace_id=6a9b19d91e658b3079 |
| 19:20:20.430 | runtime-span | cycle | execute_event_loop_cycle | trace_id=6a9b19d91e658b3079 span_id=0e4f40040527d420 session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:20:20.431 | runtime-span | model | chat model=us.anthropic.claude-sonnet-4-5-20250929-v1:0 in=6067 out=433 | trace_id=6a9b19d91e658b3079 span_id=1888d97b91e6580a session_id=aegis-sp-b-0620f5e tenant=sp-b case_id=OBS-SPB-CBF40 |
| 19:20:20.432 | runtime-span | model | chat us.anthropic.claude-sonnet-4-5-20250929-v1:0 model=us.anthropic.claude-sonnet-4-5-20250929-v1:0 in=6067 out=433 | trace_id=6a9b19d91e658b3079 span_id=964ab48e26de3769 session_id=aegis-sp-b-0620f5e request_id=df8723e3-1540-48d1 |
| 19:20:20.433 | runtime-span | span | DynamoDB.UpdateItem | trace_id=6a9b19d91e658b3079 span_id=9bc491d3fbb5faf1 session_id=aegis-sp-b-0620f5e |
| 19:20:28.347 | runtime-span | span | DynamoDB.UpdateItem | trace_id=6a9b19d91e658b3079 span_id=5ce562adb633cd1a session_id=aegis-sp-b-0620f5e |
| 19:20:28.357 | runtime-span | span | DynamoDB.GetItem | trace_id=6a9b19d91e658b3079 span_id=a276e21f01d517a4 session_id=aegis-sp-b-0620f5e |
| 19:20:28.362 | runtime-span | span | CloudWatch.PutMetricData | trace_id=6a9b19d91e658b3079 span_id=987ee8225cbd7c67 session_id=aegis-sp-b-0620f5e |
