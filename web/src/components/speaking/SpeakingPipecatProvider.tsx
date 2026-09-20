'use client';

import {PipecatClient} from '@pipecat-ai/client-js';
import {PipecatClientAudio, PipecatClientProvider} from '@pipecat-ai/client-react';
import {SmallWebRTCTransport} from '@pipecat-ai/small-webrtc-transport';
import {PropsWithChildren, useEffect, useMemo} from 'react';

export function SpeakingPipecatProvider({children}: PropsWithChildren) {
  const client = useMemo(() => new PipecatClient({
    transport: new SmallWebRTCTransport(),
    enableMic: true,
    enableCam: false,
  }), []);

  useEffect(() => () => {
    void client.disconnect();
  }, [client]);

  return <PipecatClientProvider client={client}>
    {children}
    <PipecatClientAudio />
  </PipecatClientProvider>;
}
