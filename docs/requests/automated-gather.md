# Automated Gather Item Creation - Complete Implementation Specification

**Version**: 2.1.0
**Last Updated**: January 2025
**Status**: In Implementation - Brain & Task Services In Progress

---

## 📋 Overview

The **Automated Gather Item Creation** feature automatically generates gather items from user messages, enriches them with AI, and manages conflicts. It provides a seamless experience for users to contribute content without manual effort.

**Key Principle**: Automated, AI-powered content collection and enrichment with **dynamic department support**.

---

## 🎯 Core Decisions (Finalized)

### Architecture Decisions
1. **Agent Framework**: `@codebuff/sdk` with OpenRouter models (reuses department `defaultModel`)
2. **Database**: MongoDB direct + Brain (Neo4j) for semantic search
3. **Task Processing**: `tasks.ft.tc` (Celery-Redis) service for async execution
4. **Real-time Updates**: WebSocket/SSE (existing infrastructure at port 3001)
5. **Content Strategy**: Expand existing gather items + iterative refinement
6. **Duplicate Detection**: LLM-based fly deduplication (90% similarity threshold, newer data retained)
7. **Processing**: Sequential by department (builds on previous, respects `codeDepNumber` order)
8. **Quality Threshold**: 80% (or department's `minQualityThreshold` if higher)
9. **Iterations**: Max 50 total across all departments (stop early if threshold met)
10. **Auto-evaluation**: Yes, auto-triggers sequentially until last department complete
11. **User Attribution**: Triggering user ID
12. **Cancellation**: Mid-process allowed, partial results preserved in MongoDB + Brain

---

## 🏗️ System Architecture

### Data Flow
```
User Click → Tasks.ft.tc (Celery) → @codebuff/sdk Agent → Content Generation
                ↓                                                    ↓
         WebSocket Progress ←─────────────────────────── MongoDB + Brain
                ↓                                                    ↓
         UI Real-time Updates                           Auto-trigger Evaluation
```

### Department Processing (Dynamic)
```
1. Query ALL departments WHERE gatherCheck = true
2. Sort by codeDepNumber ASC (1, 2, 3, ...)
3. Process sequentially:

   For each department (no hardcoded list):
   ├── Read existing gather items (MongoDB)
   ├── Get semantic context (Brain)
   ├── Get previous department results (cascading context)
   ├── Generate content batch (@codebuff/sdk with dept.defaultModel)
   ├── Deduplicate (LLM, 90% threshold, keep newer)
   ├── Save to MongoDB (aladdin-gather-{projectId})
   ├── Index in Brain (Neo4j, projectId isolation)
   ├── Check quality score
   ├── Repeat until: quality >= threshold OR total iterations >= 50
   └── Auto-trigger department evaluation
```

### Key Features
- ✅ **Dynamic Department Support**: Automatically processes ALL departments with `gatherCheck: true`
- ✅ **No Hardcoded Departments**: Works with 7, 10, or 100 departments
- ✅ **Respects codeDepNumber Order**: Sequential processing maintains dependency chain
- ✅ **Department-Specific Models**: Uses each department's `defaultModel` setting
- ✅ **Adaptive Thresholds**: Uses each department's `coordinationSettings.minQualityThreshold`

---

## 📂 Implementation Structure

### NEW FILES (25)

#### 1. Celery-Redis Service (tasks.ft.tc)
```
celery-redis/
├── app/tasks/automated_gather_tasks.py           # Main task logic (dynamic dept query)
├── app/agents/gather_content_generator.py        # @codebuff/sdk agent wrapper
├── app/agents/duplicate_detector.py              # LLM-based semantic dedup
├── app/agents/quality_analyzer.py                # Quality scoring per dept
└── tests/test_automated_gather.py                # Unit tests
```

#### 2. API Routes
```
src/app/api/v1/automated-gather/
├── start/route.ts                                # POST: Start automation
├── status/[taskId]/route.ts                     # GET: Check progress
├── cancel/[taskId]/route.ts                     # DELETE: Cancel task
└── types.ts                                     # TypeScript types

src/app/api/webhooks/
└── automated-gather-progress/route.ts           # Webhook for real-time updates
```

#### 3. UI Components
```
src/components/automated-gather/
├── AutomatedGatherButton.tsx                    # Trigger button (readiness + gather pages)
├── ProgressModal.tsx                            # Real-time progress modal
├── StatusIndicator.tsx                          # Current step indicator
└── DuplicationDisplay.tsx                       # "Weeding duplicates" visual
```

#### 4. Store & Hooks
```
src/stores/
└── automatedGatherStore.ts                      # Zustand state management

src/hooks/automated-gather/
├── useAutomatedGather.ts                        # Main automation hook
├── useGatherProgress.ts                         # Progress tracking
└── useGatherWebSocket.ts                        # Real-time WebSocket updates
```

#### 5. Documentation
```
docs/features/
├── automated-gather-creation.md                 # This file
└── brain-requirements.md                        # Brain service enhancement needs

docs/implementation/
└── automated-gather-implementation.md           # Technical implementation guide
```

#### 6. Tests
```
tests/e2e/
└── automated-gather.spec.ts                     # E2E test suite

celery-redis/tests/
├── test_automated_gather_tasks.py              # Task logic tests
├── test_duplicate_detection.py                 # Dedup algorithm tests
└── test_dynamic_departments.py                 # Dynamic dept handling tests
```

---

### MODIFIED FILES (8)

```
✏️  src/app/(frontend)/dashboard/project/[id]/project-readiness/page.tsx
    ├── Import AutomatedGatherButton
    ├── Add button to header (enabled when gatherCount >= 1)
    └── Show ProgressModal when active

✏️  src/app/(frontend)/dashboard/project/[id]/gather/GatherPageClient.tsx
    ├── Import AutomatedGatherButton
    ├── Add button to page header
    └── Show real-time item updates during automation

✏️  src/lib/db/gatherDatabase.ts
    ├── Add isAutomated: boolean field
    ├── Add automationMetadata: { taskId, department, iteration, qualityScore, basedOnNodes }
    └── Add query methods: getAutomatedItems(), getItemsByDepartment()

✏️  src/lib/brain/client.ts
    ├── Add batchCreateNodes() method for bulk operations
    ├── Add searchDuplicates() method (semantic similarity search)
    └── Add getDepartmentContext() method (aggregated context retrieval)

✏️  src/lib/task-service/types.ts
    └── Add AutomatedGatherTaskData interface

✏️  src/lib/task-service/client.ts
    └── Add submitAutomatedGather() method

✏️  src/lib/agents/events/websocket-server.ts
    └── Add 'automated-gather' event channel subscription

✏️  src/collections/ProjectReadiness.ts
    └── Add automationStatus: { taskId, status, startedAt, completedAt } field
```

---

## 🔧 Technical Implementation

### 1. Dynamic Department Query (Celery Task)
```python
# celery-redis/app/tasks/automated_gather_tasks.py

@celery_app.task(bind=True, name='automated_gather_creation')
def automated_gather_creation(self, task_data):
    """
    Main task for automated gather creation
    IMPORTANT: Handles dynamic departments (no hardcoded list)
    """
    project_id = task_data['project_id']
    user_id = task_data['user_id']
    max_iterations = task_data.get('max_iterations', 50)

    # 1. Read existing gather items from MongoDB
    gather_items = read_gather_items(project_id)

    # 2. Get Brain context (semantic search)
    brain_context = get_brain_context(project_id)

    # 3. DYNAMIC: Query departments with gatherCheck=true, sorted by codeDepNumber
    departments = query_departments_for_automation(project_id)
    # Returns: [
    #   { id, slug, name, codeDepNumber, gatherCheck, defaultModel, minQualityThreshold },
    #   ...
    # ]

    total_iterations = 0
    processed_departments = []

    for dept in departments:
        # Skip if gatherCheck is false (defensive check)
        if not dept['gatherCheck']:
            continue

        dept_iterations = 0
        quality_score = 0

        # Use department-specific threshold (default 80)
        threshold = dept.get('coordinationSettings', {}).get('minQualityThreshold', 80)

        # Use department-specific model
        model = dept.get('defaultModel', 'anthropic/claude-sonnet-4.5')

        # Send progress update via WebSocket
        send_websocket_event({
            'type': 'department_started',
            'department': dept['slug'],
            'department_name': dept['name'],
            'threshold': threshold,
            'model': model
        })

        # Iteration loop for this department
        while quality_score < threshold and total_iterations < max_iterations:
            # Get context from ALL previously processed departments (cascading)
            previous_dept_context = [
                processed_departments[i] for i in range(len(processed_departments))
            ]

            # Generate content batch using @codebuff/sdk
            new_items = generate_content_batch(
                project_id=project_id,
                department=dept,
                existing_context=gather_items + brain_context,
                previous_departments=previous_dept_context,
                model=model  # Use dept-specific model
            )

            # Deduplicate (LLM-based, 90% similarity, keep newer)
            send_websocket_event({'type': 'deduplicating', 'department': dept['slug']})
            deduplicated = deduplicate_items(new_items, gather_items)

            # Save to MongoDB
            saved_items = save_to_gather_db(
                project_id,
                deduplicated,
                user_id,
                automation_metadata={
                    'taskId': self.request.id,
                    'department': dept['slug'],
                    'iteration': dept_iterations + 1,
                    'qualityScore': quality_score
                }
            )

            # Index in Brain (Neo4j with projectId isolation)
            index_in_brain(project_id, saved_items, dept)

            # Update gather items list
            gather_items.extend(saved_items)

            # Check quality (department-specific scoring)
            quality_score = analyze_department_quality(
                project_id, dept, gather_items
            )

            total_iterations += 1
            dept_iterations += 1

            # Send progress update
            send_websocket_event({
                'type': 'iteration_complete',
                'department': dept['slug'],
                'department_name': dept['name'],
                'iteration': dept_iterations,
                'total_iterations': total_iterations,
                'quality_score': quality_score,
                'items_created': len(saved_items),
                'threshold': threshold
            })

        # Department complete - trigger evaluation
        trigger_department_evaluation(project_id, dept['codeDepNumber'])

        # Store department results for next department's context
        processed_departments.append({
            'department': dept['slug'],
            'name': dept['name'],
            'quality_score': quality_score,
            'iterations': dept_iterations,
            'items_created': len([i for i in gather_items if i.get('automationMetadata', {}).get('department') == dept['slug']])
        })

        send_websocket_event({
            'type': 'department_complete',
            'department': dept['slug'],
            'department_name': dept['name'],
            'quality_score': quality_score,
            'iterations_used': dept_iterations
        })

    # Final completion event
    send_websocket_event({
        'type': 'automation_complete',
        'total_iterations': total_iterations,
        'departments_processed': len(processed_departments),
        'items_created': len([i for i in gather_items if i.get('isAutomated')]),
        'summary': processed_departments
    })

    return {
        'status': 'completed',
        'iterations': total_iterations,
        'departments_processed': len(processed_departments),
        'items_created': len([i for i in gather_items if i.get('isAutomated')])
    }


def query_departments_for_automation(project_id):
    """
    DYNAMIC department query - no hardcoded departments
    """
    # Query Payload CMS for departments
    payload_client = get_payload_client()

    departments = payload_client.find({
        'collection': 'departments',
        'where': {
            'gatherCheck': {'equals': True},
            'isActive': {'equals': True}
        },
        'sort': 'codeDepNumber',
        'limit': 1000  # Support up to 1000 departments
    })

    return departments['docs']
```

### 2. Duplicate Detection (LLM-based)
```python
# celery-redis/app/agents/duplicate_detector.py

def deduplicate_items(new_items, existing_items):
    """
    Use LLM to detect semantic duplicates
    Keep newer items, discard older duplicates
    """
    deduplicated = []

    for new_item in new_items:
        is_duplicate = False

        # Check against existing items
        for existing in existing_items:
            similarity = check_semantic_similarity(
                new_item['content'],
                existing['content']
            )

            if similarity > 0.90:  # 90% similarity threshold
                is_duplicate = True
                break

        if not is_duplicate:
            deduplicated.append(new_item)

    return deduplicated


def check_semantic_similarity(text1, text2):
    """
    Use LLM to calculate semantic similarity
    """
    from codebuff import CodeBuffSDK

    sdk = CodeBuffSDK(
        api_key=os.getenv('OPENROUTER_API_KEY'),
        model="anthropic/claude-sonnet-4.5"  # Fast model for similarity
    )

    prompt = f"""Rate the semantic similarity between these two texts on a scale of 0.0 to 1.0:

Text 1: {text1[:500]}  # Truncate for efficiency
Text 2: {text2[:500]}

Return ONLY the numeric score (e.g., 0.85). No explanation."""

    response = sdk.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10
    )

    try:
        score = float(response.choices[0].message.content.strip())
        return min(max(score, 0.0), 1.0)  # Clamp to 0-1
    except:
        return 0.0  # Default to not duplicate if parsing fails
```

### 3. Content Generation (Department-Aware)
```python
# celery-redis/app/agents/gather_content_generator.py

from codebuff import CodeBuffSDK

def generate_content_batch(project_id, department, existing_context, previous_departments, model):
    """
    Generate gather items for a department using @codebuff/sdk
    Uses department-specific model from defaultModel field
    """
    sdk = CodeBuffSDK(
        api_key=os.getenv('OPENROUTER_API_KEY'),
        model=model  # Use department's model preference
    )

    # Build cascading context from ALL previous departments
    prev_context = "\n".join([
        f"**{dept['name']}** (Quality: {dept['quality_score']}%):\n{dept.get('summary', 'N/A')}"
        for dept in previous_departments
    ])

    # Format existing gather items
    existing_summary = format_gather_items(existing_context[-20:])  # Last 20 items for context

    prompt = f"""You are generating gather items for the **{department['name']}** department in a movie production project.

**Your Role**: {department.get('description', 'Generate detailed content for this department')}

**Previous Department Context** (Build upon this):
{prev_context if prev_context else "No previous context yet (this is the first department)"}

**Existing Gather Items Summary**:
{existing_summary}

**Task**: Generate 5-10 NEW gather items that:
1. Build upon insights from previous departments (especially {previous_departments[-1]['name'] if previous_departments else 'the overall project'})
2. Provide rich, detailed content specific to {department['name']}
3. Are NOT duplicates of existing content (check summaries above)
4. Cover different aspects/angles of {department['name']} (e.g., technical specs, creative vision, practical considerations)
5. Are production-ready and actionable

**Output Format** (JSON array):
[
  {{
    "content": "Detailed content here (200-500 words)",
    "summary": "One-line summary (max 100 chars)",
    "context": "Why this matters for {department['name']}"
  }},
  ...
]

Return ONLY the JSON array. No explanation."""

    response = sdk.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000
    )

    try:
        items = json.loads(response.choices[0].message.content)
        return items
    except json.JSONDecodeError:
        # Fallback: try to extract JSON from response
        content = response.choices[0].message.content
        match = re.search(r'\[.*\]', content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return []
```

### 4. UI Components

#### AutomatedGatherButton.tsx
```tsx
// src/components/automated-gather/AutomatedGatherButton.tsx

export function AutomatedGatherButton({ projectId, gatherCount, onSuccess }: Props) {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const { startAutomation, isLoading } = useAutomatedGather(projectId)

  const isEnabled = gatherCount >= 1

  const handleClick = async () => {
    if (!isEnabled) {
      toast.error('At least 1 gather item required to start automation')
      return
    }

    try {
      await startAutomation()
      setIsModalOpen(true)

      // Redirect to project-readiness after starting
      router.push(`/dashboard/project/${projectId}/project-readiness`)
    } catch (error) {
      toast.error('Failed to start automation')
    }
  }

  return (
    <>
      <Button
        onClick={handleClick}
        disabled={!isEnabled || isLoading}
        className="bg-gradient-to-r from-purple-600 to-blue-600"
      >
        <Sparkles className="mr-2 h-4 w-4" />
        {isLoading ? 'Starting...' : 'Automate Gather'}
      </Button>

      <ProgressModal
        projectId={projectId}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />

      {!isEnabled && (
        <Tooltip>
          <TooltipTrigger asChild>
            <Info className="ml-2 h-4 w-4 text-muted-foreground" />
          </TooltipTrigger>
          <TooltipContent>
            Create at least 1 gather item to enable automation
          </TooltipContent>
        </Tooltip>
      )}
    </>
  )
}
```

#### ProgressModal.tsx
```tsx
// src/components/automated-gather/ProgressModal.tsx

export function ProgressModal({ projectId, isOpen, onClose }: Props) {
  const progress = useGatherWebSocket(projectId)
  const { cancelAutomation } = useAutomatedGather(projectId)

  const isComplete = progress.status === 'completed'
  const canCancel = !isComplete && progress.status !== 'cancelling'

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-purple-500" />
            Automated Gather Creation
          </DialogTitle>
          <DialogDescription>
            Generating rich content for all departments with gather check enabled
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Current Department */}
          {progress.currentDepartment && (
            <div className="rounded-lg border border-purple-500/20 bg-purple-500/5 p-4">
              <div className="flex items-center gap-3">
                {progress.status === 'deduplicating' ? (
                  <Filter className="h-5 w-5 text-amber-500 animate-pulse" />
                ) : (
                  <Loader2 className="h-5 w-5 text-purple-500 animate-spin" />
                )}
                <div>
                  <p className="text-lg font-semibold text-white">
                    {progress.status === 'deduplicating'
                      ? `Weeding duplicates in ${progress.currentDepartmentName}...`
                      : `Processing: ${progress.currentDepartmentName}`
                    }
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Using {progress.currentModel || 'default'} model • Target: {progress.currentThreshold}%
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Quality Progress</span>
              <span className="font-semibold">{progress.qualityScore}% / {progress.currentThreshold || 80}%</span>
            </div>
            <Progress
              value={(progress.qualityScore / (progress.currentThreshold || 80)) * 100}
              className="h-3"
            />
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-3 gap-4">
            <StatCard
              icon={<Hash className="h-4 w-4" />}
              label="Iterations"
              value={`${progress.iterationCount} / ${progress.maxIterations}`}
            />
            <StatCard
              icon={<Target className="h-4 w-4" />}
              label="Quality Score"
              value={`${progress.qualityScore}%`}
            />
            <StatCard
              icon={<FileText className="h-4 w-4" />}
              label="Items Created"
              value={progress.itemsCreated}
            />
          </div>

          {/* Department Progress */}
          {progress.departments && progress.departments.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium">Department Progress</h4>
              <div className="space-y-1">
                {progress.departments.map(dept => (
                  <div key={dept.slug} className="flex items-center justify-between rounded-md bg-slate-800/40 px-3 py-2">
                    <div className="flex items-center gap-2">
                      {dept.status === 'completed' && <CheckCircle className="h-4 w-4 text-green-500" />}
                      {dept.status === 'processing' && <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />}
                      {dept.status === 'pending' && <Circle className="h-4 w-4 text-slate-500" />}
                      <span className="text-sm">{dept.name}</span>
                    </div>
                    {dept.qualityScore > 0 && (
                      <span className="text-sm text-muted-foreground">{dept.qualityScore}%</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Completion Message */}
          {isComplete && (
            <Alert className="border-green-500/40 bg-green-500/10">
              <CheckCircle className="h-4 w-4 text-green-500" />
              <AlertTitle>Automation Complete!</AlertTitle>
              <AlertDescription>
                Created {progress.itemsCreated} gather items across {progress.departmentsProcessed} departments.
                Evaluations are running sequentially.
              </AlertDescription>
            </Alert>
          )}

          {/* Action Buttons */}
          <div className="flex justify-between">
            <Button
              variant="destructive"
              onClick={() => cancelAutomation()}
              disabled={!canCancel}
            >
              {progress.status === 'cancelling' ? 'Cancelling...' : 'Cancel Automation'}
            </Button>

            {isComplete && (
              <Button onClick={onClose}>
                Close
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
```

---

## 🧪 Brain Service Requirements

### ✅ Implementation Status: IN PROGRESS

**Service**: brain.ft.tc
**Status**: API endpoints being implemented
**Documentation**: `docs/features/need-brain-service-api-requirements.md`

### New Endpoints (Being Implemented)

#### 1. Batch Node Creation ⏳
```
POST /api/v1/nodes/batch
```
**Status**: Implementation in progress at brain.ft.tc
**Expected**: Ready for testing soon

#### 2. Duplicate Search ⏳
```
POST /api/v1/search/duplicates
```
**Status**: Implementation in progress at brain.ft.tc
**Expected**: Ready for testing soon

#### 3. Department Context ⏳
```
GET /api/v1/context/department
```
**Status**: Implementation in progress at brain.ft.tc
**Expected**: Ready for testing soon

#### 4. Coverage Analysis ⏳
```
POST /api/v1/analyze/coverage
```
**Status**: Implementation in progress at brain.ft.tc
**Expected**: Ready for testing soon

**📄 Complete API contract**: `docs/features/need-brain-service-api-requirements.md`

---

## 🔄 Task Queue Configuration

### ✅ Implementation Status: IN PROGRESS

**Service**: tasks.ft.tc (Celery-Redis)
**Status**: Queue configuration being implemented
**Documentation**: `docs/features/need-task-queue-requirements.md`

### Configuration Updates (Being Implemented)

#### Task Type Registration ⏳
- **Task**: `automated_gather_creation`
- **Queue**: `cpu_intensive`
- **Timeout**: 600 seconds (10 minutes)
- **Retry**: 3 attempts with exponential backoff
- **Priority**: 1 (high)
- **Status**: Configuration in progress at tasks.ft.tc

#### Worker Configuration ⏳
- **Concurrency**: 4 workers
- **Memory Limit**: 2GB per worker
- **Result Backend**: Redis (1 hour expiry)
- **Status**: Infrastructure setup in progress

**📄 Complete infrastructure specs**: `docs/features/need-task-queue-requirements.md`

---

## 📊 Database Schema Updates

### MongoDB (Gather Collection)
```typescript
interface GatherItem {
  _id: ObjectId
  projectId: string
  content: string
  summary: string
  context: string
  imageUrl?: string
  documentUrl?: string
  extractedText?: string
  duplicateCheckScore?: number

  // NEW: Automation fields
  isAutomated: boolean                    // True if created by automation
  automationMetadata?: {
    taskId: string                        // Celery task ID
    department: string                    // Department slug
    departmentName: string                // Department display name
    iteration: number                     // Which iteration (1-50)
    qualityScore: number                  // Quality at creation time
    basedOnNodes: string[]                // Brain node IDs used as context
    model: string                         // OpenRouter model used
  }

  iterationCount?: number
  createdAt: Date
  createdBy: string                       // User ID (triggering user)
  lastUpdated: Date
}
```

### Neo4j (Brain) Nodes
```cypher
// New node type for automated gather items
(:GatherItem:Automated {
  id: string,
  projectId: string,
  content: string,
  department: string,
  departmentName: string,
  iteration: number,
  qualityScore: number,
  model: string,
  createdAt: datetime,
  createdBy: string
})

// Relationships
(:GatherItem)-[:BASED_ON]->(:GatherItem)         // References to context items
(:GatherItem)-[:BELONGS_TO]->(:Department)       // Department association
(:GatherItem)-[:GENERATED_IN]->(:AutomationTask) // Link to task
(:GatherItem)-[:FOLLOWS]->(:GatherItem)          // Sequential dependency
```

---

## 🎯 Success Criteria

### Functional Requirements ✅
- Button enabled when `gatherCount >= 1`
- Processes ALL departments with `gatherCheck: true` (dynamic query)
- Respects `codeDepNumber` order (sequential)
- Uses each department's `defaultModel` setting
- Achieves department's `minQualityThreshold` (default 80%)
- Max 50 iterations total (stops early if threshold met)
- Real-time progress via WebSocket (no polling)
- "Weeding duplicates" visual step
- Auto-triggers evaluations sequentially
- Cancellation preserves partial results
- Redirects to project-readiness page

### Technical Requirements ✅
- Uses `@codebuff/sdk` for content generation
- MongoDB + Brain (Neo4j) dual storage
- LLM-based duplicate detection (90% threshold)
- Newer data retained in duplicates
- ProjectId isolation (MongoDB + Brain)
- Attribution to triggering user
- Dynamic department support (no hardcoded lists)
- Handles 7, 10, 100+ departments gracefully

### Performance Targets ✅
- Average completion: <10 minutes
- Token optimization: Batch operations
- WebSocket latency: <500ms
- No database bottlenecks
- Graceful error recovery

---

## 📅 Implementation Timeline

### ✅ Phase 0: Service Requirements (COMPLETE)
- ✅ Brain Service API requirements documented
- ✅ Task Queue infrastructure requirements documented
- ✅ Brain service implementation initiated at brain.ft.tc
- ✅ Task Queue configuration initiated at tasks.ft.tc

### 🔄 Phase 1: External Services (IN PROGRESS)
**Brain Service (brain.ft.tc)**:
- ⏳ POST /api/v1/nodes/batch
- ⏳ POST /api/v1/search/duplicates
- ⏳ GET /api/v1/context/department
- ⏳ POST /api/v1/analyze/coverage

**Task Queue (tasks.ft.tc)**:
- ⏳ Task type registration
- ⏳ Worker configuration
- ⏳ Monitoring setup

**Next**: Wait for services to be ready for testing

### 📋 Phase 2: Main App Task Implementation (PENDING)
**Location**: `celery-redis/` in main app
- ⏸️ `app/tasks/automated_gather_tasks.py` - Main orchestration
- ⏸️ `app/agents/gather_content_generator.py` - @codebuff/sdk wrapper
- ⏸️ `app/agents/duplicate_detector.py` - LLM deduplication
- ⏸️ `app/agents/quality_analyzer.py` - Quality scoring
- ⏸️ Helper modules (MongoDB, Brain client, Payload client, WebSocket)

**Prerequisites**: Brain API endpoints + Task Queue ready

### 📋 Phase 3: Main App API & Backend (PENDING)
- ⏸️ API endpoints (start, status, cancel)
- ⏸️ Task service client methods
- ⏸️ Zustand store implementation
- ⏸️ Error handling & retries
- ⏸️ WebSocket integration

**Prerequisites**: Task implementation complete

### 📋 Phase 4: UI Components (PENDING)
- ⏸️ AutomatedGatherButton
- ⏸️ ProgressModal with WebSocket
- ⏸️ Status indicators
- ⏸️ Dedup visual feedback
- ⏸️ Page integrations

**Prerequisites**: API & Backend complete

### 📋 Phase 5: Testing & Polish (PENDING)
- ⏸️ Integration testing with Brain + Task Queue
- ⏸️ E2E tests (dynamic depts)
- ⏸️ Unit tests (all components)
- ⏸️ Performance optimization
- ⏸️ Edge cases & errors
- ⏸️ Documentation updates

**Prerequisites**: All components complete

---

## 🚦 Current Status

### ✅ Completed
- Architecture design finalized
- Requirements documented for all services
- Brain service implementation initiated (brain.ft.tc)
- Task Queue configuration initiated (tasks.ft.tc)

### ⏳ In Progress (External Services)
- **brain.ft.tc**: 4 API endpoints being implemented
- **tasks.ft.tc**: Queue configuration and monitoring setup

### ⏸️ Awaiting
- **Main App Implementation**: Waiting for Brain + Task Queue to be ready for testing
- **Testing Phase**: Will begin after all components integrated

### 🎯 Next Milestone
**"Ready for Testing" Signal**
- When Brain service endpoints are deployed
- When Task Queue is configured
- Then proceed with Main App implementation (Phase 2-4)

---

## 🚀 Implementation Roadmap

### Current Phase: External Services Setup ⏳

**Brain Service (brain.ft.tc)**: API endpoints in development
**Task Queue (tasks.ft.tc)**: Infrastructure configuration in progress

### Next: Main App Implementation (Awaiting Services)

Once Brain + Task Queue services are ready for testing:
1. Implement Celery task logic (Phase 2)
2. Build API endpoints & backend (Phase 3)
3. Create UI components (Phase 4)
4. Integration testing (Phase 5)

### Testing Readiness Checklist

**Before proceeding with main app implementation, verify**:
- [ ] Brain service endpoints deployed and accessible
- [ ] Task Queue configured and workers running
- [ ] API documentation available
- [ ] Test credentials/access provided
- [ ] Service health checks passing

**📢 Notify when services are ready for testing to proceed with main app implementation.**

---

## 🎯 Design Principles Confirmed

✅ **No hardcoded departments** - Dynamic query from Payload CMS
✅ **No loopholes** - All edge cases covered in requirements
✅ **Production-ready** - Error handling, monitoring, scaling designed
✅ **Dynamic and scalable** - Handles 7 to 1000+ departments gracefully

**Status**: External services in progress → Main app implementation awaiting green light 🚦
