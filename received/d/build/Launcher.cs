using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

internal static class Program
{
    [STAThread]
    private static void Main()
    {
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;
        string pythonw = Path.Combine(baseDir, "runtime", "pythonw.exe");
        string script = Path.Combine(baseDir, "app_main.py");

        if (!File.Exists(pythonw) || !File.Exists(script))
        {
            MessageBox.Show(
                "发行包不完整：缺少 runtime 目录或 app_main.py。\n请重新解压完整压缩包。",
                "车牌识别系统", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }

        var start = new ProcessStartInfo
        {
            FileName = pythonw,
            Arguments = "\"" + script + "\"",
            WorkingDirectory = baseDir,
            UseShellExecute = false
        };
        try
        {
            Process.Start(start);
        }
        catch (Exception ex)
        {
            MessageBox.Show("启动失败：" + ex.Message, "车牌识别系统",
                MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}
