export default {
  template: `
    <div ref="cytoscape" style="width: 100%; height: 100%; position: relative;">
    </div>
  `,
  props: {
    elements: {
      type: Object,
      default: () => ({ nodes: [], edges: [] })
    },
    style: {
      type: Array,
      default: () => [
        {
          selector: 'node',
          style: {
            'background-color': '#666',
            'label': 'data(label)',
            'color': '#fff',
            'text-valign': 'center',
            'text-halign': 'center',
            'overlay-padding': '6px',
            'z-index': '10'
          }
        },
        {
          selector: 'node:selected',
          style: {
            'background-color': '#0d6efd',
            'border-width': '2px',
            'border-color': '#0d6efd'
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 3,
            'line-color': '#ccc',
            'target-arrow-color': '#ccc',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier'
          }
        },
        {
          selector: 'edge:selected',
          style: {
            'line-color': '#0d6efd',
            'target-arrow-color': '#0d6efd',
            'width': 4
          }
        }
      ]
    },
    layout: {
      type: Object,
      default: () => ({ name: 'cose' })
    }
  },
  data() {
    return {
      cy: null
    }
  },
  mounted() {
    this.initCytoscape()
  },
  beforeUnmount() {
    if (this.cy) {
      this.cy.destroy()
    }
  },
  methods: {
    initCytoscape() {
      // Load Cytoscape if not already loaded
      if (typeof cytoscape === 'undefined') {
        const script = document.createElement('script')
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.26.0/cytoscape.min.js'
        script.onload = () => {
          this.createGraph()
        }
        document.head.appendChild(script)
      } else {
        this.createGraph()
      }
    },
    createGraph() {
      this.cy = cytoscape({
        container: this.$refs.cytoscape,
        elements: this.elements,
        style: this.style,
        layout: this.layout,
        minZoom: 0.1,
        maxZoom: 4,
        wheelSensitivity: 0.2
      })
      
      // Bind events
      this.cy.on('tap', 'node', (evt) => {
        const node = evt.target
        this.$emit('node-click', {
          id: node.id(),
          data: node.data()
        })
      })
      
      this.cy.on('tap', 'edge', (evt) => {
        const edge = evt.target
        this.$emit('edge-click', {
          id: edge.id(),
          source: edge.source().id(),
          target: edge.target().id(),
          data: edge.data()
        })
      })
      
      this.cy.on('tap', (evt) => {
        if (evt.target === this.cy) {
          this.$emit('canvas-click', {
            position: evt.position
          })
        }
      })
      
      this.cy.on('dragfree', 'node', (evt) => {
        const node = evt.target
        this.$emit('node-drag-end', {
          id: node.id(),
          position: node.position()
        })
      })
      
      this.cy.on('select', () => {
        const selected = this.cy.$(':selected').map(ele => ({
          id: ele.id(),
          type: ele.isNode() ? 'node' : 'edge'
        }))
        this.$emit('selection-change', selected)
      })
    },
    // Public methods that can be called from Python
    addNode(nodeData) {
      if (this.cy) {
        this.cy.add({
          group: 'nodes',
          data: nodeData.data,
          position: nodeData.position || { x: 100, y: 100 }
        })
      }
    },
    updateNode(nodeId, updates) {
      if (this.cy) {
        const node = this.cy.getElementById(nodeId)
        if (node) {
          if (updates.data) {
            node.data(updates.data)
          }
          if (updates.position) {
            node.position(updates.position)
          }
        }
      }
    },
    deleteNode(nodeId) {
      if (this.cy) {
        const node = this.cy.getElementById(nodeId)
        if (node) {
          node.remove()
        }
      }
    },
    addEdge(edgeData) {
      if (this.cy) {
        this.cy.add({
          group: 'edges',
          data: edgeData.data
        })
      }
    },
    updateEdge(edgeId, updates) {
      if (this.cy) {
        const edge = this.cy.getElementById(edgeId)
        if (edge && updates.data) {
          edge.data(updates.data)
        }
      }
    },
    deleteEdge(edgeId) {
      if (this.cy) {
        const edge = this.cy.getElementById(edgeId)
        if (edge) {
          edge.remove()
        }
      }
    },
    applyLayout(layoutName, options = {}) {
      if (this.cy) {
        const layout = this.cy.layout({
          name: layoutName,
          ...options
        })
        layout.run()
      }
    },
    fitView() {
      if (this.cy) {
        this.cy.fit()
      }
    },
    getElements() {
      if (this.cy) {
        return {
          nodes: this.cy.nodes().map(n => ({
            data: n.data(),
            position: n.position()
          })),
          edges: this.cy.edges().map(e => ({
            data: e.data()
          }))
        }
      }
      return { nodes: [], edges: [] }
    }
  },
  watch: {
    elements: {
      handler(newElements) {
        if (this.cy && newElements) {
          // Update graph with new elements
          this.cy.elements().remove()
          this.cy.add(newElements.nodes || [])
          this.cy.add(newElements.edges || [])
          this.applyLayout(this.layout.name)
        }
      },
      deep: true
    }
  }
}