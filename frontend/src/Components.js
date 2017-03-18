import React, { Component } from 'react'

class Ticker extends Component {

  componentDidMount() {
    this.timerID = setInterval(() => this.tick(), 1000)
  }

  componentWillUnmount() {
    clearInterval(this.timerID)
  }

}

export class Clock extends Ticker {
  constructor(props) {
    super(props)
    this.state = {date: new Date()}
  }

  tick() {
    this.setState({
      date: new Date()
    })
  }

  render() {
    return (<span>{this.state.date.toLocaleTimeString()}</span>)
  }
}

import {RadialChart, XYPlot, XAxis, YAxis, HorizontalGridLines, LineSeries} from 'react-vis'

export class Graph extends Component {

  constructor(props) {
    super(props)
    this.data = []
    var x
    for (x = 0; x < 2; x += 0.1) {
      this.data.push({x: x, y: x*x + Math.random()})
    }
    for (x = 2; x < 5; x += 0.1) {
      this.data.push({x: x, y: 5 + Math.random()})
    }
    for (x = 5; x < 10; x += 0.1) {
      this.data.push({x: x, y: 3 + Math.random()})
    }
  }

  render() {
    return (<XYPlot width={300}
                    height={300}>
              <HorizontalGridLines />
              <LineSeries data={this.data}/>
              <XAxis />
              <YAxis />
            </XYPlot>)
  }
}

export class MiniGraph extends Component {

  constructor(props) {
    super(props)
    this.data = []
    var x
    for (x = 0; x < 2; x += 0.1) {
      this.data.push({x: x, y: x*x + Math.random()})
    }
    for (x = 2; x < 5; x += 0.1) {
      this.data.push({x: x, y: 5 + Math.random()})
    }
    for (x = 5; x < 10; x += 0.1) {
      this.data.push({x: x, y: 3 + Math.random()})
    }
  }

  render() {
    return (<RadialChart data={[{angle: 2}, {angle: 3}, {angle: 5}]} width={50} height={50}/>)
  }
}

import {Table, Button} from 'semantic-ui-react'

export class ExpandingTable extends Component {

  constructor(props) {
    super(props)
    this.state = {rows: [
      (<Table.Row><Table.Cell>asdf</Table.Cell><Table.Cell>fdsa</Table.Cell></Table.Row>),
      (<Table.Row><Table.Cell>b</Table.Cell><Table.Cell>asdfdsafdasdf: <Clock/></Table.Cell></Table.Row>)
    ]}
  }

  go() {
    this.timerID = setInterval(() => this.step(), 1000)
  }

  step() {
    if (this.state.rows.length < 10) {
      this.setState({
        rows: this.state.rows.concat([<Table.Row><Table.Cell>blah</Table.Cell><Table.Cell>{this.state.rows.length}</Table.Cell></Table.Row>])
      })
    } else {
      clearInterval(this.timerID)
    }
  }

  render() {
    return (<div>
              <Button onClick={() => this.go()}>Go</Button>
              <Table>
                {this.state.rows}
              </Table>
            </div>)
  }

}
