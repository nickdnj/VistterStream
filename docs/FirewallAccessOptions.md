# Accessing VistterStream Behind a Firewall

This guide summarizes network-access strategies that allow VistterStudio operators to connect to VistterStream deployments that sit behind restrictive firewalls. Each option highlights prerequisites, security considerations, and operational trade-offs so teams can choose the approach that best matches their infrastructure and compliance requirements.

## 1. Site-to-Site or Client VPN

A virtual private network (VPN) extends a private network across the internet and is often the most straightforward way to provide secure, bidirectional connectivity between VistterStudio and on-premises VistterStream instances.

### How it works
* Deploy a VPN gateway (e.g., OpenVPN, WireGuard, IPsec) at the facility hosting VistterStream.
* Configure firewall rules to allow inbound VPN traffic on the chosen protocol/port.
* Provision VistterStudio clients with credentials to join the VPN.

### Pros
* Mature, well-understood security model with centralized authentication and logging.
* Full network access enables timelines, schedules, and other VistterStudio features without additional proxying.
* Scales to multiple users and services.

### Cons
* Requires management of VPN infrastructure and certificates/keys.
* Broad network exposure if access controls are not carefully scoped (consider split tunneling, per-service ACLs).

## 2. Reverse Proxy in a Demilitarized Zone (DMZ)

A reverse proxy or application gateway placed in a DMZ can forward HTTPS requests from the internet to the internal VistterStream API endpoints.

### How it works
* Deploy an NGINX, HAProxy, or cloud-managed reverse proxy in the DMZ.
* Terminate TLS at the proxy and forward only necessary routes (e.g., `/api/timelines`, `/api/schedules`).
* Configure the firewall to allow inbound HTTPS to the proxy and outbound traffic from the proxy to the internal VistterStream host.

### Pros
* Granular control over exposed endpoints.
* Central place to enforce WAF rules, rate limiting, and authentication (e.g., OAuth, mutual TLS).
* Easier to audit than full VPN tunnels.

### Cons
* Requires an additional server or managed gateway.
* Needs careful hardening to prevent proxy compromise.

## 3. Secure Tunneling Services (SSH, Cloudflare Tunnel, Tailscale Funnel)

On-demand tunnels expose selected services to the internet without opening inbound firewall ports directly to the VistterStream host.

### How it works
* Install a tunneling agent on the VistterStream network (e.g., `ssh -R`, Cloudflare Tunnel, Tailscale Funnel).
* The agent initiates an outbound connection to a relay service, which VistterStudio accesses over the internet.
* Optionally layer authentication (SSO, tokens) at the tunnel entry point.

### Pros
* Minimal network changes—firewalls typically permit outbound HTTPS or SSH.
* Quick to set up for temporary or low-volume remote access.
* Built-in identity integrations in many managed tunneling products.

### Cons
* Reliance on third-party relay infrastructure (evaluate trust and compliance requirements).
* Performance depends on tunnel provider latency.
* Must monitor agents to ensure tunnels stay healthy.

## 4. Remote Desktop Gateway + Local VistterStudio

If direct API exposure is not permitted, use a remote desktop gateway to provide administrators with access to a workstation on the internal network.

### How it works
* Deploy a Remote Desktop Gateway (RD Gateway) or similar service in the DMZ.
* Administrators authenticate to the gateway and launch a remote session on an internal workstation running VistterStudio.
* VistterStudio interacts with VistterStream over the local network within the remote session.

### Pros
* No VistterStream services exposed to the internet.
* Centralized monitoring of administrator sessions.

### Cons
* User experience depends on remote desktop performance.
* Requires management of RD Gateway infrastructure.

## 5. API Synchronization via Message Broker

For workflows that do not require real-time editing, synchronize timeline and schedule updates through a broker or cloud service.

### How it works
* VistterStudio exposes a synchronization API endpoint (REST or event-based) that publishes timeline and schedule changes to a cloud-accessible broker (e.g., AWS SQS, Azure Service Bus).
* An on-premises agent polls the broker and applies updates to VistterStream inside the firewall.
* Responses or status updates are pushed back through the same broker and consumed by the VistterStudio endpoint.

### Implementation notes
* Plan the VistterStudio API contract early so the broker payloads mirror existing timeline/schedule schemas and can be evolved with versioning.
* Secure the endpoint with OAuth or signed tokens because it will be reachable from outside the internal network.
* Consider batching or debouncing publishes to minimize broker costs and reduce the chance of conflicting updates.

### Pros
* No inbound connectivity from the internet to the internal network.
* Naturally supports auditing and retry logic.

### Cons
* Additional latency; not ideal for live control.
* Requires building or configuring synchronization agents.

## Security Recommendations
* **Zero Trust Principles:** Enforce least privilege (network ACLs, API scopes) regardless of the connectivity option.
* **Strong Authentication:** Use multi-factor authentication and short-lived credentials for VPN/tunnel users.
* **TLS Everywhere:** Encrypt traffic end-to-end, including internal hops when feasible.
* **Monitoring and Logging:** Capture logs from VPNs, proxies, and agents; monitor for anomalies.
* **Regular Audits:** Review firewall rules and exposed services quarterly to ensure they match operational needs.

## Decision Criteria Checklist
| Requirement | Recommended Option |
|-------------|--------------------|
| Long-term, multi-user administrative access | VPN or reverse proxy |
| Temporary/low-volume access with minimal network changes | Secure tunneling service |
| Strict no-inbound policy | Broker synchronization or remote desktop gateway |
| Need for granular HTTP-level controls | Reverse proxy |
| Requirement to avoid third-party relays | VPN or reverse proxy |

Select the combination of techniques that aligns with the organization's compliance posture, operational maturity, and desired user experience for VistterStudio operators.
