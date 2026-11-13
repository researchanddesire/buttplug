// Local developer-process control for the exact Freerouting job we launched.
// Uses the router's normal stop API; never edits its board, rules or copper.
// The JDK attach helper makes the existing CLI job save its partial SES normally.
import java.awt.Frame;
import java.lang.instrument.Instrumentation;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Path;
import com.sun.tools.attach.VirtualMachine;
public class RouterControl {
 public static void main(String[]args)throws Exception{
  if(args.length!=3)throw new IllegalArgumentException("PID AGENT_JAR STATUS_OUTPUT");
  VirtualMachine vm=VirtualMachine.attach(args[0]);
  try{vm.loadAgent(args[1],args[2]);}finally{vm.detach();}
 }
 static Object field(Object o,String name)throws Exception{Field f=o.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(o);}
 public static void agentmain(String output,Instrumentation ignored)throws Exception{
  Path path=Path.of(output).toAbsolutePath();
  if(!path.toString().endsWith("/hardware/pcb/evt1/dock-main/routing/main-pass2-stop.json"))throw new IllegalArgumentException("Unrecognized job output");
  for(Frame f:Frame.getFrames()){
   if(!f.getClass().getName().equals("app.freerouting.gui.BoardFrame")||!f.getTitle().contains("main-pass2"))continue;
   Object panel=field(f,"board_panel"),handling=field(panel,"board_handling");
   Object settings=handling.getClass().getMethod("get_settings").invoke(handling);
   Object routing=settings.getClass().getField("autoroute_settings").get(settings);
   Object pass=routing.getClass().getMethod("get_start_pass_no").invoke(routing);
   Thread thread=(Thread)field(handling,"interactive_action_thread");
   thread.getClass().getMethod("request_stop").invoke(thread);
   Files.writeString(path,"{\"job\":\"main-pass2\",\"pass_no\":"+pass+",\"normal_stop_API_requested\":true,\"board_modified_by_controller\":false}\n");
   return;
  }
  throw new IllegalStateException("Exact main-pass2 router frame not found");
 }
}
