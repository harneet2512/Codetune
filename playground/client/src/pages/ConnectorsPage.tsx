import { useConnectorWorkbench } from '../hooks/useConnectorWorkbench'
import { ConnectorList } from '../components/connectors/ConnectorList'
import { ToolExplorer } from '../components/connectors/ToolExplorer'

export function ConnectorsPage() {
  const { state, dispatch, connect, disconnect, runTool } = useConnectorWorkbench()

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      <ConnectorList
        state={state}
        onSelect={(service) => dispatch({ type: 'SELECT_CONNECTOR', id: service })}
        onConnect={connect}
        onDisconnect={disconnect}
      />
      <ToolExplorer
        state={state}
        dispatch={dispatch}
        onConnect={connect}
        onRunTool={runTool}
      />
    </div>
  )
}
