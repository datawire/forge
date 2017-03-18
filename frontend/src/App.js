import React, { Component } from 'react'
import './App.css'
import "../node_modules/react-vis/dist/style.css"
import "../semantic/dist/semantic.min.css"
import io from 'socket.io-client'

import { Image, Header, Card, Dimmer, Segment, Loader, Progress, Grid, Menu, Button, Icon, Input, Modal, Message, Step } from 'semantic-ui-react'

class CreateService extends Component {

  constructor(props) {
    super(props)
    this.state = {
      step: 0
    }
  }

  go(e) {
    if (e.key === 'Enter') {
      this.setState({step: this.state.step + 1,
                     service: e.target.value})
      this.timerID = setInterval(() => this.step(), 250)
    }
  }

  step() {
    if (this.state.step < 6) {
      this.setState({step: this.state.step + 1})
    } else {
      clearInterval(this.timerID)
    }
  }

  render() {
    if (this.state.step === 0) {
      return (
        <Input fluid icon='github' iconPosition='left'
               label={{tag: true, content: 'Create Service'}} labelPosition='right'
               placeholder='http://github.com/organization/servicename'
               onKeyPress={(e) => this.go(e)} />
      )
    } else {
      var steps = [
        {icon: "server", title: "Deployment", desc: "Kubernetes deployment manifest"},
        {icon: "sitemap", title: "Service", desc: "Kubernetes service manifest"},
        {icon: "find", title: "Ingress", desc: "Kubernetes ingress resource"},
        {icon: "database", title: "Postgres", desc: "Creating postgres dependency"},
        {icon: "cubes", title: "Redis", desc: "Creating redis dependency"}
      ]
      var stack = []
      for (var i = 0; i < Math.min(this.state.step, 5); i++) {
        var active = (i===this.state.step - 1)
        stack.push(
          <Step key={steps[i].title} completed={!active} active={active}>
            <Icon name={steps[i].icon}/>
            <Step.Content>
              <Step.Title>{steps[i].title}</Step.Title>
              <Step.Description>{steps[i].desc}</Step.Description>
            </Step.Content>
          </Step>
        )
      }

      var done = (this.state.step === 6)
      return (
        <Grid>
          <Grid.Row columns={1}>
            <Grid.Column>
              <Progress percent={this.state.step*100/6}/>
            </Grid.Column>
          </Grid.Row>
          <Grid.Row columns={2}>
            <Grid.Column>
              <Step.Group fluid vertical>
                {stack}
              </Step.Group>
            </Grid.Column>
            <Grid.Column verticalAlign="middle">
              <Segment><Dimmer active={!done}><Loader disabled={done} active={!done}>Creating...</Loader></Dimmer><Button onClick={() => this.props.onDone(this.state.service)} fluid>Dismiss</Button></Segment>
            </Grid.Column>
          </Grid.Row>
        </Grid>
      )
    }
  }
}

import {RadialChart} from 'react-vis'

const rateStyle = {
  position: 'absolute',
  width: 100,
  height: 100,
  textAlign: 'center',
  verticalAlign: 'middle',
  lineHeight: '100px'
}

function abbrev(mag) {
  if (mag === 1000) {
    return 'K'
  }
  if (mag === 1000000) {
    return 'M'
  }
}

function format(n) {
  if (n < 100) {
    return n.toFixed(1)
  }

  var mag
  for (mag of [1000, 1000000]) {
    if ((n / mag) < 100) {
      break;
    }
  }

  return (n/mag).toFixed(1) + abbrev(mag)
}

class ServiceCard extends Component {
  render() {
    let stats = this.props.stats
    let rate = stats.good + stats.bad + stats.slow
    let data = [{angle: stats.good, color: 'green'},
                {angle: stats.slow, color: 'yellow'},
                {angle: stats.bad, color: 'red'}]
    if (rate === 0.0) {
      data = [{angle: 1, color: 'grey'}]
    }
    return (<Card key={this.props.name} raised>
              <Card.Content>
                <div style={{float: 'right'}}>
            <Header style={rateStyle}>{rate !== 0 ? format(rate) : "--"}</Header>
                  <RadialChart width={100} height={100} innerRadius={25} colorType='literal' data={data} />
                </div>
                <Card.Header>{this.props.name}</Card.Header>
                <Card.Meta>{this.props.owner}</Card.Meta>
              </Card.Content>
            </Card>)
  }
}

class ServiceGroup extends Component {
  render() {
    if (this.props.children.length > 0) {
      return (<Card.Group>{this.props.children}</Card.Group>)
    } else {
      return (<Message>No services...</Message>)
    }
  }
}

class App extends Component {

  constructor(props) {
    super(props)
    this.state = {
      count: 0,
      open: false,
      services: []
    }
    this.url = 'http://' + window.location.hostname + ':' + window.location.port
    if (process.env.NODE_ENV === 'development') {
      this.url = process.env.REACT_APP_BLACKBIRD_RTM
    }
  }

  componentDidMount() {
    this.socket = io(this.url)
    this.socket.on('message', (msg) => {
      if (this.state.count % 10 === 0) {
        console.log(msg)
      }
      this.setState({count: this.state.count + 1})
    })
    this.socket.on('dirty', (srv) => {
      this.update(srv)
    })

    fetch(this.url + '/get')
      .then((response) => response.json())
      .then((result) => {
        for (let svc of result) {
          this.update(svc)
        }
      })
  }

  update(srv) {
    let found = false
    for (let service of this.state.services) {
      if (service.name === srv.name) {
        service.owner = srv.owner
        service.stats = srv.stats
        found = true
        break
      }
    }
    if (!found) {
      this.state.services.push(srv)
    }
    this.setState({services: this.state.services})
  }

  create() {
    this.setState({open: true})
  }

  created(service) {
    this.setState({open: false})
    this.update({name: service, owner: 'hodor@org.io', stats: {good: 0.0, bad: 0.0, slow: 0.0}})
  }

  render() {
    let services = []
    for (let srv of this.state.services) {
      services.push(<ServiceCard key={srv.name} {...srv}/>)
    }

    let on = this.state.count % 2 === 0
    return (
      <div className="App">
        <Grid padded textAlign="left">
          <Grid.Row centered>
            <Grid.Column width={1}/>
            <Grid.Column width={14} textAlign="center">
        <h1><Image src="https://www.datawire.io/wp-content/uploads/2017/01/blackbird.png" avatar/>Blackbird Service Registry</h1>
            </Grid.Column>
            <Grid.Column textAlign="right" width={1}>
              <Icon.Group size='big'>
                <Icon name='cloud'/>
                <Icon corner color={on ? 'red' : 'grey'} disabled={!on} name='heartbeat'/>
              </Icon.Group>
            </Grid.Column>
          </Grid.Row>
          <Grid.Row>
            <Grid.Column width={3}>
              <Menu vertical>
                <Menu.Item name='settings'>Settings</Menu.Item>
                <Menu.Item name='admin'>Administration</Menu.Item>
                <Menu.Item name='create' onClick={()=>this.create()}>Create Service</Menu.Item>
                <Menu.Item name='search'><Input icon='search' placeholder='Search services...'/></Menu.Item>
              </Menu>
            </Grid.Column>
            <Grid.Column width={13}>
              <ServiceGroup>{services}</ServiceGroup>
              <Modal open={this.state.open}>
                <Modal.Header>Create a Service</Modal.Header>
                <Modal.Content><CreateService onDone={(service) => this.created(service)}/></Modal.Content>
              </Modal>
            </Grid.Column>
          </Grid.Row>
        </Grid>
      </div>
    )
  }
}

export default App
