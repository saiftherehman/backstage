"""D-Bus interface the GNOME Shell island talks to.

Bus name io.github.saiftherehman.Backstage, object /io/github/saiftherehman/Backstage. Methods are quick;
anything slow (speech, AI answers) reports back later through signals.
"""

from gi.repository import Gio, GLib

BUS_NAME = "io.github.saiftherehman.Backstage"
OBJECT_PATH = "/io/github/saiftherehman/Backstage"

INTERFACE = """
<node>
  <interface name="io.github.saiftherehman.Backstage">
    <method name="GetState"><arg type="s" direction="out" name="state"/></method>
    <method name="StartSession">
      <arg type="s" direction="in" name="kind"/>
      <arg type="s" direction="in" name="title"/>
      <arg type="s" direction="out" name="id"/>
    </method>
    <method name="StopSession"/>
    <method name="OfferFrame">
      <arg type="s" direction="in" name="path"/>
      <arg type="i" direction="in" name="x"/>
      <arg type="i" direction="in" name="y"/>
      <arg type="i" direction="in" name="width"/>
      <arg type="i" direction="in" name="height"/>
    </method>
    <method name="AnalyseNow"/>
    <method name="SetProvider"><arg type="s" direction="in" name="name"/></method>
    <method name="LoadScript"><arg type="s" direction="in" name="text"/></method>
    <method name="LoadDocument"><arg type="s" direction="in" name="path"/></method>
    <method name="JumpPrompter"><arg type="i" direction="in" name="line"/></method>
    <signal name="StateChanged"><arg type="s" name="state"/></signal>
    <signal name="Transcript"><arg type="s" name="speaker"/><arg type="s" name="text"/></signal>
    <signal name="PrompterMoved"><arg type="i" name="line"/></signal>
    <signal name="AnswerStarted"><arg type="s" name="reason"/></signal>
    <signal name="Answer"><arg type="s" name="reason"/><arg type="s" name="answer"/></signal>
    <signal name="ShareModeChanged"><arg type="s" name="mode"/></signal>
    <signal name="Error"><arg type="s" name="message"/></signal>
  </interface>
</node>
"""

SIGNAL_TYPES = {
    "StateChanged": "(s)", "Transcript": "(ss)", "PrompterMoved": "(i)",
    "AnswerStarted": "(s)", "Answer": "(ss)", "ShareModeChanged": "(s)", "Error": "(s)",
}


class Service:
    def __init__(self, make_app):
        """make_app(emit) builds the app once the bus is ready."""
        self._make_app = make_app
        self.app = None
        self._connection = None
        self._info = Gio.DBusNodeInfo.new_for_xml(INTERFACE).interfaces[0]
        Gio.bus_own_name(Gio.BusType.SESSION, BUS_NAME, Gio.BusNameOwnerFlags.NONE,
                         self._on_bus, None, self._on_lost)

    def _on_bus(self, connection, name):
        self._connection = connection
        connection.register_object(OBJECT_PATH, self._info, self._on_call, None, None)
        self.app = self._make_app(self.emit)

    def _on_lost(self, connection, name):
        raise SystemExit(f"Could not own {BUS_NAME}; is the helper already running?")

    def emit(self, signal, *args):
        """Safe to call from any thread."""
        params = GLib.Variant(SIGNAL_TYPES[signal], args)
        GLib.idle_add(self._emit, signal, params)

    def _emit(self, signal, params):
        self._connection.emit_signal(None, OBJECT_PATH, BUS_NAME, signal, params)
        return GLib.SOURCE_REMOVE

    def _on_call(self, connection, sender, path, interface, method, params, invocation):
        app, args = self.app, params.unpack()
        try:
            result = None
            if method == "GetState":
                result = GLib.Variant("(s)", (app.state(),))
            elif method == "StartSession":
                result = GLib.Variant("(s)", (app.start_session(*args),))
            elif method == "StopSession":
                app.stop_session()
            elif method == "OfferFrame":
                app.offer_frame(*args)
            elif method == "AnalyseNow":
                app.analyse_now()
            elif method == "SetProvider":
                app.set_provider(*args)
            elif method == "LoadScript":
                app.load_script(*args)
            elif method == "LoadDocument":
                app.load_document(*args)
            elif method == "JumpPrompter":
                app.jump_prompter(*args)
            invocation.return_value(result)
        except Exception as error:
            invocation.return_dbus_error("io.github.saiftherehman.Backstage.Error", str(error))
