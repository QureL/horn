from controller.controller import Controller
from audio.audio import AudioDeviceKeepr, AudioRecorder
from audio.speaker_windows import SpeakderPyTTSx3
from config.config import GPTChatConfig
from processor.processor import STT_ProcessorLocal
from gpt.gpt import GPTReuqestor, ConcurrentGPTBridge
import enum
import logging
from config.const import *
class ControllerState(enum.Enum):
    CONTROLLER_STOPPING = 0
    CONTROLLER_RUNNING = 1


class GPTChatController():

    __instance = None

    def __init__(self,) -> None:
        self.audio_device_keeper = AudioDeviceKeepr()
        self.speaker = SpeakderPyTTSx3()
        self.stt_processor = STT_ProcessorLocal(stt_model='base', stt_language='en')
        self.gpt_requestor = GPTReuqestor()
        self.gpt_bridge = ConcurrentGPTBridge(self.gpt_requestor, speaker=self.speaker)
        self.recorder = AudioRecorder(self.audio_device_keeper, output_pipe=self.stt_processor, is_chat=True, secs=10)
        self.state = ControllerState.CONTROLLER_STOPPING
        self.config = GPTChatConfig()
        speed = self.config.get_config(GPT_SPEAK_SPEED)
        if speed != None:
            self.speaker.set_speed(float(speed))
        
    @classmethod
    def get_instance(cls):
        if cls.__instance is None:
            cls.__instance = GPTChatController()
        return cls.__instance

    def set_gpt_system_command(self, cmd):
        self.gpt_requestor.set_system_command(cmd)

    def display_audio_input_devices(self):
        return self.audio_device_keeper.display_devices(input=True)

    def display_audio_output_devices(self):
        return self.speaker.show_voices()

    def start_thread(self):
        self.speaker.start()
        self.stt_processor.start()
        self.gpt_bridge.start()
        self.recorder.start()
        self.state = ControllerState.CONTROLLER_RUNNING

    def stop_thread(self):
        self.speaker.terminate()
        self.stt_processor.terminate()
        self.gpt_bridge.terminate()
        self.recorder.terminate()
        self.state = ControllerState.CONTROLLER_STOPPING

    def record_or_pause(self):
        if self.state == ControllerState.CONTROLLER_STOPPING:
            logging.info("start threading now")
            self.start_thread()
        else:
            self.recorder.switch()

    def input_human_message(self, msg):
        self.gpt_bridge.put(msg)

    # 绑定whisper speech to text 后的结果，后触发信号的callback
    def bind_stt_message_trigger(self, callback):
        self.stt_processor.set_callback(callback)

    # 绑定 gpt response到达后的callback函数
    def bind_gpt_message_trigger(self, callback):
        self.gpt_bridge.set_callback(callback)


    def set_attribute(self, **args):
        self.gpt_requestor.set_attribute(**args)
        self.stt_processor.set_attribute(**args)
        self.speaker.set_attribute(**args)
        input_device = args.get('input_device', None)
        if input_device:
            self.recorder.select_device(input_device)

    def pause_speaking(self):
        self.speaker.pause()

    def set_session(self, name):
        self.gpt_requestor.set_session(name)

    def reload_setting(self):
        
        system_cmd = self.config.get_config(GPT_SYSTEM_CMD)
        if len(system_cmd) > 0:
            self.gpt_requestor.set_system_command(system_cmd)
        
        context_cnt = self.config.get_config(GPT_CONTEXT_CNT)
        if context_cnt != None:
            self.gpt_requestor.set_attribute(context_cnt=int(context_cnt))

        speed = self.config.get_config(GPT_SPEAK_SPEED)
        if speed != None:
            self.speaker.set_speed(float(speed))

    