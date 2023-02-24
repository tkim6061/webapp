import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const URL = 'ws://localhost:8000';
  const [message, setMessage] = useState([]);
  const [messages, setMessages] = useState([]);
  const [ws, setWs] = useState(new WebSocket(URL));

  useEffect(() => {
    ws.onopen = () => {
      ws.send('Connection opened')
      console.log('WebSocket Connected');
    }

    ws.onmessage = (evt) => {
      const recv = JSON.parse(evt.data);
      const recvTime = parseInt(recv.delta * 50);
      const maxLen = 100;
      let text = "["
      for (let i = 0; i < 100; i++){
        if(i == 99 && i < recvTime){
          text += '|';
        } else if (i == recvTime) {
          text += '|';
        } else {
          text += '-';
        }
      }
      if (recv.count < 10){
        recv.count = `0${recv.count}`
      }
      text += "]";
      const message = `num:+${recv.msg_num} d:+${recv.delta} n:+${recv.count} m:+${recv.mean} o:+${recv.std_dev} 0ms ${text} 2000ms`;
      setMessages(messages => [...messages, message].slice(-25));

      console.log(message);
    }

    return () => {
      ws.onclose = () => {
        ws.send('Connection closed');
        console.log('WebSocket Disconnected');
        setWs(new WebSocket(URL));
        ws.close();
      }
    }
  }, [ws.onmessage, ws.onopen, ws.onclose, message]);

  return (
    <div className="App">
      <ul>
        {messages.map((message, index) =>
          <li key={index}>
            {message}
          </li>
        )}
      </ul>
    </div>
  );
}

export default App;
