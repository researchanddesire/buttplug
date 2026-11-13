// Request the normal stop on our exact CLI-created router worker. A command-
// line job may have no BoardFrame, so match the launched command and worker.
import java.lang.instrument.Instrumentation;
import java.nio.file.Files;
import java.nio.file.Path;
public class RouterStop {
 public static void agentmain(String output,Instrumentation ignored)throws Exception{
  Path path=Path.of(output).toAbsolutePath();
  String prefix=path.getFileName().toString().replace("-stop.json","");
  if(!prefix.matches("main-pass[0-9]+")||!path.getParent().toString().endsWith("/hardware/pcb/evt1/dock-main/routing"))throw new IllegalArgumentException("Unrecognized output");
  String command=ProcessHandle.current().info().commandLine().orElse("");
  if(!command.contains("freerouting-1.9.0")||!command.contains(prefix+".dsn"))throw new IllegalStateException("Not our exact router CLI job");
  Class<?> type=Class.forName("app.freerouting.interactive.BatchAutorouterThread");
  for(Thread thread:Thread.getAllStackTraces().keySet())if(type.isInstance(thread)){
   Object handling=thread.getClass().getField("hdlg").get(thread);
   Object settings=handling.getClass().getMethod("get_settings").invoke(handling);
   Object routing=settings.getClass().getField("autoroute_settings").get(settings);
   Object pass=routing.getClass().getMethod("get_start_pass_no").invoke(routing);
   thread.getClass().getMethod("request_stop").invoke(thread);
   Files.writeString(path,"{\"job\":\""+prefix+"\",\"pass_no\":"+pass+",\"normal_stop_API_requested\":true,\"board_modified_by_controller\":false}\n");
   return;
  }
  throw new IllegalStateException("Router worker already ended or not found");
 }
}
