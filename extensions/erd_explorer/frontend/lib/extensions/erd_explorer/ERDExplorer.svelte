<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  
  // Entity relationship data (hardcoded for now)
  let entities = {
    "Realm": {
      "fields": ["id", "name", "description", "created_at", "updated_at"],
      "relationships": {
        "treasury": {"type": "OneToOne", "target": "Treasury", "field": "realm"}
      },
      "count": 1,
      "position": { x: 400, y: 50 },
      "expanded": false
    },
    "User": {
      "fields": ["id", "profile_picture_url", "created_at", "updated_at"],
      "relationships": {
        "profiles": {"type": "ManyToMany", "target": "UserProfile", "field": "users"},
        "human": {"type": "OneToOne", "target": "Human", "field": "user"},
        "citizen": {"type": "OneToOne", "target": "Citizen", "field": "user"},
        "transfers_from": {"type": "OneToMany", "target": "Transfer", "field": "from_user"},
        "transfers_to": {"type": "OneToMany", "target": "Transfer", "field": "to_user"},
        "trades_a": {"type": "OneToMany", "target": "Trade", "field": "user_a"},
        "trades_b": {"type": "OneToMany", "target": "Trade", "field": "user_b"},
        "owned_lands": {"type": "OneToMany", "target": "Land", "field": "owner_user"}
      },
      "count": 150,
      "position": { x: 200, y: 200 },
      "expanded": false
    },
    "Human": {
      "fields": ["id", "name", "date_of_birth", "created_at", "updated_at"],
      "relationships": {
        "user": {"type": "OneToOne", "target": "User", "field": "human"},
        "identities": {"type": "OneToMany", "target": "Identity", "field": "human"}
      },
      "count": 150,
      "position": { x: 50, y: 350 },
      "expanded": false
    },
    "Identity": {
      "fields": ["id", "type", "metadata", "created_at", "updated_at"],
      "relationships": {
        "human": {"type": "ManyToOne", "target": "Human", "field": "identities"}
      },
      "count": 300,
      "position": { x: 250, y: 500 },
      "expanded": false
    },
    "Citizen": {
      "fields": ["id", "created_at", "updated_at"],
      "relationships": {
        "user": {"type": "OneToOne", "target": "User", "field": "citizen"}
      },
      "count": 120,
      "position": { x: 350, y: 350 },
      "expanded": false
    },
    "Organization": {
      "fields": ["id", "name", "created_at", "updated_at"],
      "relationships": {},
      "count": 25,
      "position": { x: 500, y: 200 },
      "expanded": false
    },
    "Codex": {
      "fields": ["id", "name", "code", "url", "checksum", "created_at", "updated_at"],
      "relationships": {
        "call": {"type": "OneToOne", "target": "Call", "field": "codex"}
      },
      "count": 8,
      "position": { x: 600, y: 100 },
      "expanded": false
    },
    "Transfer": {
      "fields": ["id", "amount", "created_at", "updated_at"],
      "relationships": {
        "from_user": {"type": "ManyToOne", "target": "User", "field": "transfers_from"},
        "to_user": {"type": "ManyToOne", "target": "User", "field": "transfers_to"}
      },
      "count": 450,
      "position": { x: 400, y: 400 },
      "expanded": false
    },
    "Treasury": {
      "fields": ["id", "created_at", "updated_at"],
      "relationships": {
        "realm": {"type": "OneToOne", "target": "Realm", "field": "treasury"}
      },
      "count": 1,
      "position": { x: 600, y: 50 },
      "expanded": false
    }
  };

  // Sample data for entity instances (hardcoded for now)
  let sampleData = {
    "Realm": [
      { id: "realm_1", name: "Demo Realm", description: "A demonstration realm", created_at: "2024-01-01" },
    ],
    "User": [
      { id: "user_1", profile_picture_url: "https://example.com/pic1.jpg", created_at: "2024-01-01" },
      { id: "user_2", profile_picture_url: "https://example.com/pic2.jpg", created_at: "2024-01-02" },
      { id: "user_3", profile_picture_url: "https://example.com/pic3.jpg", created_at: "2024-01-03" },
    ],
    "Human": [
      { id: "human_1", name: "Alice Johnson", date_of_birth: "1990-05-15", created_at: "2024-01-01" },
      { id: "human_2", name: "Bob Smith", date_of_birth: "1985-08-22", created_at: "2024-01-02" },
      { id: "human_3", name: "Carol Davis", date_of_birth: "1992-12-03", created_at: "2024-01-03" },
    ],
    "Identity": [
      { id: "identity_1", type: "passport", metadata: "US-123456789", created_at: "2024-01-01" },
      { id: "identity_2", type: "driver_license", metadata: "DL-987654321", created_at: "2024-01-02" },
      { id: "identity_3", type: "national_id", metadata: "NID-456789123", created_at: "2024-01-03" },
    ]
  };

  let selectedEntity = null;
  let selectedRecord = null;
  let currentPage = 1;
  let pageSize = 10;
  let isDragging = false;
  let dragOffset = { x: 0, y: 0 };

  // SVG dimensions
  let svgWidth = 800;
  let svgHeight = 600;

  function handleEntityClick(entityName: string) {
    if (selectedEntity === entityName) {
      entities[entityName].expanded = !entities[entityName].expanded;
    } else {
      // Collapse previously selected entity
      if (selectedEntity) {
        entities[selectedEntity].expanded = false;
      }
      selectedEntity = entityName;
      entities[entityName].expanded = true;
      selectedRecord = null;
      currentPage = 1;
    }
    entities = { ...entities }; // Trigger reactivity
  }

  function handleRecordClick(record: any) {
    selectedRecord = record;
  }

  function getRelationshipColor(relType: string): string {
    switch (relType) {
      case 'OneToOne': return '#4F46E5';
      case 'OneToMany': return '#059669';
      case 'ManyToOne': return '#DC2626';
      case 'ManyToMany': return '#7C2D12';
      default: return '#6B7280';
    }
  }

  function getEntityColor(entityName: string): string {
    if (entityName === 'Realm') return '#8B5CF6';
    if (entityName === 'User') return '#3B82F6';
    if (entityName === 'Human') return '#10B981';
    if (entityName === 'Identity') return '#F59E0B';
    return '#6B7280';
  }

  function drawRelationshipLine(from: any, to: any, relType: string) {
    if (!entities[to]) return '';
    
    const fromPos = entities[from].position;
    const toPos = entities[to].position;
    
    const color = getRelationshipColor(relType);
    
    return `<line x1="${fromPos.x + 75}" y1="${fromPos.y + 40}" x2="${toPos.x + 75}" y2="${toPos.y + 40}" 
            stroke="${color}" stroke-width="2" marker-end="url(#arrowhead-${relType})"/>`;
  }

  function startDrag(event: MouseEvent, entityName: string) {
    isDragging = true;
    const rect = event.currentTarget.getBoundingClientRect();
    dragOffset.x = event.clientX - entities[entityName].position.x;
    dragOffset.y = event.clientY - entities[entityName].position.y;
    
    function onMouseMove(e: MouseEvent) {
      if (isDragging) {
        entities[entityName].position.x = e.clientX - dragOffset.x;
        entities[entityName].position.y = e.clientY - dragOffset.y;
        entities = { ...entities };
      }
    }
    
    function onMouseUp() {
      isDragging = false;
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    }
    
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  }

  function getPaginatedData(entityName: string) {
    const data = sampleData[entityName] || [];
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    return data.slice(startIndex, endIndex);
  }

  function getTotalPages(entityName: string) {
    const data = sampleData[entityName] || [];
    return Math.ceil(data.length / pageSize);
  }

  onMount(() => {
    // Initialize with Realm as the starting point
    selectedEntity = 'Realm';
    entities['Realm'].expanded = true;
  });
</script>

<div class="erd-explorer">
  <div class="header">
    <h1 class="text-2xl font-bold text-gray-900 mb-4">
      {$_('extensions.erd_explorer.title')}
    </h1>
    <p class="text-gray-600 mb-6">
      {$_('extensions.erd_explorer.description')}
    </p>
  </div>

  <div class="explorer-container">
    <!-- ERD Visualization Panel -->
    <div class="erd-panel">
      <div class="panel-header">
        <h2 class="text-lg font-semibold text-gray-800">Entity Relationship Diagram</h2>
        <div class="legend">
          <div class="legend-item">
            <div class="legend-color" style="background-color: #4F46E5;"></div>
            <span>OneToOne</span>
          </div>
          <div class="legend-item">
            <div class="legend-color" style="background-color: #059669;"></div>
            <span>OneToMany</span>
          </div>
          <div class="legend-item">
            <div class="legend-color" style="background-color: #DC2626;"></div>
            <span>ManyToOne</span>
          </div>
          <div class="legend-item">
            <div class="legend-color" style="background-color: #7C2D12;"></div>
            <span>ManyToMany</span>
          </div>
        </div>
      </div>
      
      <div class="erd-canvas">
        <svg width={svgWidth} height={svgHeight} class="erd-svg">
          <!-- Define arrow markers -->
          <defs>
            <marker id="arrowhead-OneToOne" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#4F46E5" />
            </marker>
            <marker id="arrowhead-OneToMany" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#059669" />
            </marker>
            <marker id="arrowhead-ManyToOne" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#DC2626" />
            </marker>
            <marker id="arrowhead-ManyToMany" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#7C2D12" />
            </marker>
          </defs>
          
          <!-- Relationship lines -->
          {#each Object.entries(entities) as [entityName, entity]}
            {#each Object.entries(entity.relationships) as [relName, rel]}
              {@html drawRelationshipLine(entityName, rel.target, rel.type)}
            {/each}
          {/each}
          
          <!-- Entity nodes -->
          {#each Object.entries(entities) as [entityName, entity]}
            <g class="entity-node" 
               transform="translate({entity.position.x}, {entity.position.y})"
               on:mousedown={(e) => startDrag(e, entityName)}>
              
              <rect width="150" height="80" 
                    fill={getEntityColor(entityName)}
                    stroke={selectedEntity === entityName ? '#1F2937' : '#E5E7EB'}
                    stroke-width={selectedEntity === entityName ? 3 : 1}
                    rx="8" 
                    class="entity-rect cursor-pointer"
                    on:click={() => handleEntityClick(entityName)} />
              
              <text x="75" y="25" text-anchor="middle" class="entity-title" fill="white">
                {entityName}
              </text>
              
              <text x="75" y="45" text-anchor="middle" class="entity-count" fill="white" opacity="0.8">
                {entity.count} records
              </text>
              
              <text x="75" y="65" text-anchor="middle" class="entity-action" fill="white" opacity="0.9">
                Click to explore
              </text>
            </g>
          {/each}
        </svg>
      </div>
    </div>

    <!-- Data Panel -->
    <div class="data-panel">
      {#if selectedEntity}
        <div class="panel-header">
          <h2 class="text-lg font-semibold text-gray-800">
            {selectedEntity} Data
            <span class="text-sm text-gray-500">({entities[selectedEntity].count} total)</span>
          </h2>
        </div>

        {#if entities[selectedEntity].expanded}
          <div class="data-content">
            <!-- Entity Fields -->
            <div class="fields-section">
              <h3 class="text-md font-medium text-gray-700 mb-2">Fields</h3>
              <div class="fields-list">
                {#each entities[selectedEntity].fields as field}
                  <span class="field-tag">{field}</span>
                {/each}
              </div>
            </div>

            <!-- Relationships -->
            {#if Object.keys(entities[selectedEntity].relationships).length > 0}
              <div class="relationships-section">
                <h3 class="text-md font-medium text-gray-700 mb-2">Relationships</h3>
                <div class="relationships-list">
                  {#each Object.entries(entities[selectedEntity].relationships) as [relName, rel]}
                    <div class="relationship-item">
                      <span class="relationship-name">{relName}</span>
                      <span class="relationship-type" style="color: {getRelationshipColor(rel.type)}">
                        {rel.type}
                      </span>
                      <span class="relationship-target">{rel.target}</span>
                    </div>
                  {/each}
                </div>
              </div>
            {/if}

            <!-- Sample Data Table -->
            <div class="data-table-section">
              <h3 class="text-md font-medium text-gray-700 mb-2">Sample Data</h3>
              
              {#if sampleData[selectedEntity] && sampleData[selectedEntity].length > 0}
                <div class="table-container">
                  <table class="data-table">
                    <thead>
                      <tr>
                        {#each entities[selectedEntity].fields.slice(0, 4) as field}
                          <th>{field}</th>
                        {/each}
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {#each getPaginatedData(selectedEntity) as record}
                        <tr class="table-row" 
                            class:selected={selectedRecord === record}
                            on:click={() => handleRecordClick(record)}>
                          {#each entities[selectedEntity].fields.slice(0, 4) as field}
                            <td>{record[field] || '-'}</td>
                          {/each}
                          <td>
                            <button class="view-btn" on:click={() => handleRecordClick(record)}>
                              View
                            </button>
                          </td>
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>

                <!-- Pagination -->
                {#if getTotalPages(selectedEntity) > 1}
                  <div class="pagination">
                    <button 
                      class="page-btn" 
                      disabled={currentPage === 1}
                      on:click={() => currentPage = Math.max(1, currentPage - 1)}>
                      Previous
                    </button>
                    
                    <span class="page-info">
                      Page {currentPage} of {getTotalPages(selectedEntity)}
                    </span>
                    
                    <button 
                      class="page-btn"
                      disabled={currentPage === getTotalPages(selectedEntity)}
                      on:click={() => currentPage = Math.min(getTotalPages(selectedEntity), currentPage + 1)}>
                      Next
                    </button>
                  </div>
                {/if}
              {:else}
                <div class="no-data">
                  <p class="text-gray-500">No sample data available for {selectedEntity}</p>
                </div>
              {/if}
            </div>
          </div>
        {:else}
          <div class="collapsed-message">
            <p class="text-gray-500">Click on the {selectedEntity} node to expand and view data</p>
          </div>
        {/if}
      {:else}
        <div class="no-selection">
          <p class="text-gray-500">Select an entity from the diagram to view its data</p>
        </div>
      {/if}
    </div>
  </div>

  <!-- Selected Record Details -->
  {#if selectedRecord}
    <div class="record-details">
      <div class="panel-header">
        <h2 class="text-lg font-semibold text-gray-800">Record Details</h2>
        <button class="close-btn" on:click={() => selectedRecord = null}>×</button>
      </div>
      
      <div class="record-content">
        {#each Object.entries(selectedRecord) as [key, value]}
          <div class="record-field">
            <span class="field-label">{key}:</span>
            <span class="field-value">{value}</span>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .erd-explorer {
    padding: 1rem;
    max-width: 100%;
    height: 100vh;
    overflow: hidden;
  }

  .header {
    margin-bottom: 1rem;
  }

  .explorer-container {
    display: grid;
    grid-template-columns: 1fr 400px;
    gap: 1rem;
    height: calc(100vh - 200px);
  }

  .erd-panel, .data-panel {
    background: white;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .panel-header {
    padding: 1rem;
    border-bottom: 1px solid #E5E7EB;
    background: #F9FAFB;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .legend {
    display: flex;
    gap: 1rem;
    font-size: 0.75rem;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .legend-color {
    width: 12px;
    height: 12px;
    border-radius: 2px;
  }

  .erd-canvas {
    flex: 1;
    overflow: auto;
    background: #FAFAFA;
  }

  .erd-svg {
    display: block;
  }

  .entity-node {
    cursor: move;
  }

  .entity-rect {
    filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.1));
  }

  .entity-title {
    font-weight: 600;
    font-size: 14px;
  }

  .entity-count {
    font-size: 11px;
  }

  .entity-action {
    font-size: 10px;
  }

  .data-content {
    flex: 1;
    padding: 1rem;
    overflow-y: auto;
  }

  .fields-section, .relationships-section, .data-table-section {
    margin-bottom: 1.5rem;
  }

  .fields-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .field-tag {
    background: #F3F4F6;
    color: #374151;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-family: monospace;
  }

  .relationships-list {
    space-y: 0.5rem;
  }

  .relationship-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem;
    background: #F9FAFB;
    border-radius: 4px;
    font-size: 0.875rem;
  }

  .relationship-name {
    font-weight: 500;
  }

  .relationship-type {
    font-size: 0.75rem;
    font-weight: 600;
  }

  .relationship-target {
    color: #6B7280;
  }

  .table-container {
    overflow-x: auto;
    border: 1px solid #E5E7EB;
    border-radius: 4px;
  }

  .data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
  }

  .data-table th {
    background: #F9FAFB;
    padding: 0.75rem 0.5rem;
    text-align: left;
    font-weight: 600;
    border-bottom: 1px solid #E5E7EB;
  }

  .data-table td {
    padding: 0.75rem 0.5rem;
    border-bottom: 1px solid #F3F4F6;
  }

  .table-row {
    cursor: pointer;
    transition: background-color 0.15s;
  }

  .table-row:hover {
    background: #F9FAFB;
  }

  .table-row.selected {
    background: #EBF8FF;
  }

  .view-btn {
    background: #3B82F6;
    color: white;
    padding: 0.25rem 0.5rem;
    border: none;
    border-radius: 4px;
    font-size: 0.75rem;
    cursor: pointer;
  }

  .view-btn:hover {
    background: #2563EB;
  }

  .pagination {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid #E5E7EB;
  }

  .page-btn {
    background: #F3F4F6;
    border: 1px solid #D1D5DB;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.875rem;
  }

  .page-btn:hover:not(:disabled) {
    background: #E5E7EB;
  }

  .page-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .page-info {
    font-size: 0.875rem;
    color: #6B7280;
  }

  .no-data, .collapsed-message, .no-selection {
    padding: 2rem;
    text-align: center;
  }

  .record-details {
    position: fixed;
    bottom: 1rem;
    right: 1rem;
    width: 300px;
    background: white;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    z-index: 1000;
  }

  .close-btn {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: #6B7280;
    padding: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .close-btn:hover {
    color: #374151;
  }

  .record-content {
    padding: 1rem;
    max-height: 300px;
    overflow-y: auto;
  }

  .record-field {
    display: flex;
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
  }

  .field-label {
    font-weight: 500;
    color: #374151;
    min-width: 80px;
  }

  .field-value {
    color: #6B7280;
    word-break: break-word;
  }

  @media (max-width: 1024px) {
    .explorer-container {
      grid-template-columns: 1fr;
      grid-template-rows: 400px 1fr;
    }
  }
</style>
