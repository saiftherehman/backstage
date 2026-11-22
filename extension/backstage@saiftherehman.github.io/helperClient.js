// Talks to the Backstage helper (helper/backstage/service.py) over D-Bus.

import Gio from 'gi://Gio';

const BUS_NAME = 'io.github.saiftherehman.Backstage';
const OBJECT_PATH = '/io/github/saiftherehman/Backstage';
const SERVICE_UNIT = 'backstage-helper.service';

const INTERFACE = `
<node>
  <interface name="io.github.saiftherehman.Backstage">
    <method name="GetState"><arg type="s" direction="out" name="state"/></method>
    <method name="StartSession">
      <arg type="s" direction="in" name="kind"/>
      <arg type="s" direction="in" name="title"/>
      <arg type="s" direction="out" name="id"/>
    </method>
    <method name="StopSession"/>
    <method name="OfferFrame"><arg type="s" direction="in" name="path"/></method>
    <method name="AnalyseNow"/>
    <method name="SetProvider"><arg type="s" direction="in" name="name"/></method>
    <method name="LoadScript"><arg type="s" direction="in" name="text"/></method>
    <method name="LoadDocument"><arg type="s" direction="in" name="path"/></method>
    <method name="JumpPrompter"><arg type="i" direction="in" name="line"/></method>
    <method name="SetPaused"><arg type="b" direction="in" name="paused"/></method>
    <method name="SetRecording"><arg type="s" direction="in" name="mode"/></method>
    <signal name="StateChanged"><arg type="s" name="state"/></signal>
    <signal name="Transcript"><arg type="s" name="speaker"/><arg type="s" name="text"/></signal>
    <signal name="PrompterMoved"><arg type="i" name="line"/></signal>
    <signal name="AnswerStarted"><arg type="s" name="reason"/></signal>
    <signal name="Answer"><arg type="s" name="reason"/><arg type="s" name="answer"/></signal>
    <signal name="ShareModeChanged"><arg type="s" name="mode"/></signal>
    <signal name="Error"><arg type="s" name="message"/></signal>
  </interface>
</node>`;

const HelperProxy = Gio.DBusProxy.makeProxyWrapper(INTERFACE);

export class HelperClient {
    /**
     * handlers: object with optional functions named after the signals
     * (onStateChanged, onTranscript, ...) plus onConnected(state) and
     * onDisconnected().
     */
    constructor(handlers) {
        this._handlers = handlers;
        this._signalIds = [];
        this._proxy = new HelperProxy(Gio.DBus.session, BUS_NAME, OBJECT_PATH, null, null,
            Gio.DBusProxyFlags.DO_NOT_AUTO_START);
        for (const name of ['StateChanged', 'Transcript', 'PrompterMoved',
            'AnswerStarted', 'Answer', 'ShareModeChanged', 'Error']) {
            this._signalIds.push(this._proxy.connectSignal(name,
                (proxy, sender, args) => this._handlers[`on${name}`]?.(...args)));
        }
        this._ownerId = this._proxy.connect('notify::g-name-owner', () => this._onOwnerChanged());
        this._onOwnerChanged();
        if (!this._proxy.g_name_owner)
            startHelper();
    }

    get connected() {
        return Boolean(this._proxy.g_name_owner);
    }

    async _onOwnerChanged() {
        if (!this.connected) {
            this._handlers.onDisconnected?.();
            return;
        }
        this._handlers.onConnected?.(await this.getState());
    }

    async getState() {
        const [state] = await this._proxy.GetStateAsync();
        return JSON.parse(state);
    }

    startSession(kind, title) {
        return this._proxy.StartSessionAsync(kind, title);
    }

    stopSession() {
        return this._proxy.StopSessionAsync();
    }

    offerFrame(path) {
        return this._proxy.OfferFrameAsync(path);
    }

    analyseNow() {
        return this._proxy.AnalyseNowAsync();
    }

    setProvider(name) {
        return this._proxy.SetProviderAsync(name);
    }

    loadScript(text) {
        return this._proxy.LoadScriptAsync(text);
    }

    loadDocument(path) {
        return this._proxy.LoadDocumentAsync(path);
    }

    jumpPrompter(line) {
        return this._proxy.JumpPrompterAsync(line);
    }

    setPaused(paused) {
        return this._proxy.SetPausedAsync(paused);
    }

    setRecording(mode) {
        return this._proxy.SetRecordingAsync(mode);
    }

    destroy() {
        for (const id of this._signalIds)
            this._proxy.disconnectSignal(id);
        this._proxy.disconnect(this._ownerId);
        this._proxy = null;
    }
}

// The helper normally starts with the desktop session; this covers the case
// where it was stopped or crashed.
function startHelper() {
    try {
        Gio.Subprocess.new(['systemctl', '--user', 'start', SERVICE_UNIT], Gio.SubprocessFlags.NONE);
    } catch (e) {
        console.warn(`Backstage: could not start ${SERVICE_UNIT}: ${e.message}`);
    }
}
